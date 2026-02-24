import numpy as np
import onnxruntime as rt
import pickle
import os
import sys
import signal
import csv
import time
import base64
import subprocess
from urllib.request import urlopen, Request
from colorama import Fore, Style
from azure.storage.blob import BlobClient
from time import sleep

# Decryption key
DECRYPTION_KEY_PATH = os.getenv("DECRYPTION_KEY_PATH", "")

# SAS token path. This is a mounted  (sealed) secret volume.
SAS_TOKEN_PATH = os.getenv("SAS_TOKEN_PATH", "/azure/azure-sas")

# SAS token, replace the SAS token path if set
SAS_TOKEN = os.getenv("SAS_TOKEN", "")
default_sas_token = "c3A9ciZzdD0yMDI1LTEwLTI3VDE1OjQyOjI3WiZzZT0yMDI4LTEwLTI3VDIyOjU3OjI3WiZzcHI9aHR0cHMmc3Y9MjAyNC0xMS0wNCZzcj1iJnNpZz12amFSb3RkN2RlJTJCM1F3bHpIVmFIRjJHVnllaHcxeGIzZkZpWGU5RTdZT0klM0Q="

# Azure storage name
AZURE_STORAGE_NAME = os.getenv("AZURE_STORAGE_NAME", "encrypteddatasets")

# Blob name
BLOB_NAME = os.getenv("BLOB_NAME", "dataset1.csv.enc")

# Container name
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "data")

# Threshold prediction
THRESHOLD_PREDICTION = os.getenv("TRESHOLD_PREDICTION", 0.999999)

# Decryption key output path
DECRYPTION_KEY_OUTPUT = "/app/dataset.key"

DATASET_LOCATION = "/app/downloaded_datasets/"

# Load ONNX model
sess = rt.InferenceSession("/app/models/fraud/1/model.onnx", providers=rt.get_available_providers())

# Load scaler
with open('/app/artifact/scaler.pkl', 'rb') as handle:
    scaler = pickle.load(handle)

input_name = sess.get_inputs()[0].name
output_name = sess.get_outputs()[0].name

def ask_model(query):
    prediction = sess.run([output_name], {input_name: scaler.transform(query).astype(np.float32)})
    threshold = float(THRESHOLD_PREDICTION)
    bool_answer = np.squeeze(prediction) > threshold and np.squeeze(prediction) < 1
    perc_answer = "{:.5f}".format(100 * np.squeeze(prediction)) + "%"
    return (bool_answer, perc_answer)

def fetch_secret_trustee(kpath, dest):
    if kpath.startswith("kbs:///"):
        kpath = kpath[len("kbs:///"):]
    else:
        raise Exception("Invalid decryption key path: " + kpath + ". It must start with kbs:///")
    url = f"http://127.0.0.1:8006/cdh/resource/{kpath.lstrip('/')}"
    req = Request(url)
    with urlopen(req) as resp:
        key_data = resp.read()
    with open(dest, "wb") as f:
        f.write(key_data)
    print(f"  Fetched key from {kpath} to {dest}")

def _head_n1(path):
    """Run head -n 1 on a file and return the first line for display."""
    r = subprocess.run(["head", "-n", "1", path], capture_output=True)
    return (r.stdout or b"").decode("utf-8", errors="replace").strip() or "(empty)"


def decrypt_file(file_path):
    print(f"  Decrypting: {file_path}")
    if not file_path.endswith(".enc"):
        raise ValueError(f"Expected .enc file, got: {file_path}")
    file_path_without_enc = file_path[: -len(".enc")]
    print(f"    Before (head -n 1): {_head_n1(file_path)}")
    try:
        result = subprocess.run(
            [
                "openssl", "enc", "-d", "-aes-256-cfb", "-pbkdf2",
                "-kfile", DECRYPTION_KEY_OUTPUT,
                "-in", file_path,
                "-out", file_path_without_enc,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  openssl decryption failed (exit code {e.returncode}):")
        if e.stdout:
            print(f"    stdout: {e.stdout}")
        if e.stderr:
            print(f"    stderr: {e.stderr}")
        raise
    print(f"    After (head -n 1): {_head_n1(file_path_without_enc)}")


def open_all_files_in_folder(folder_path):
    input_data = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith('.enc'):
            print(f"  Encrypted file: {filename}")
            decrypt_file(file_path)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                print(f"  Loaded: {file_path}")
                reader = list(csv.reader(f))[1:]
                input_data += reader
        except Exception as e:
            print(f"  Could not read {filename}: {e}")

    # random.shuffle(input_data)
    return input_data


def download_blob(storage_name, blob_name, container_name):
    download_file_path = DATASET_LOCATION + blob_name
    sas = 'NOT_FOUND'

    if SAS_TOKEN:
        default_sas_key_loc = "/azure/azure-sas-token"
        print("  SAS_TOKEN set; fetching secret from Trustee")
        fetch_secret_trustee(SAS_TOKEN, default_sas_key_loc)
        SAS_TOKEN_PATH = default_sas_key_loc

    try:
        with open(SAS_TOKEN_PATH, 'r') as file:
            sas = file.read()
    except FileNotFoundError:
        print("  SAS token file not found")
    except Exception as e:
        print(f"  Error reading SAS token: {e}")

    if sas == 'NOT_FOUND' or sas == '':
        print("  Using default SAS token (no token from file)")
        sas = base64.b64decode(default_sas_token).decode('utf-8')

    blob_client = BlobClient.from_blob_url("https://" + storage_name + ".blob.core.windows.net/" + container_name + "/" + blob_name + "?" + sas)

    print(f"  Downloading {container_name}/{blob_name} -> {download_file_path}")
    with open(download_file_path, "wb") as download_file:
        blob_data = blob_client.download_blob()
        blob_data.readinto(download_file)
    print(f"  Download complete")

    if blob_name.endswith(".enc"):
        return True
    return False

def add_default_dataset():
    print("  Using default dataset: default.csv")
    os.system("cp /app/default_datasets/default.csv " + DATASET_LOCATION)
    return False

def inspect_data(data):
    print()
    print(f"Loaded {len(data)} transactions")
    print("Inspecting credit card transactions:")

    i = 0
    for query in data:
        b, p = ask_model([query])
        b_t = "FALSE"
        stop_print=False
        if b:
            b_t = Fore.RED + "TRUE" + Style.RESET_ALL
            stop_print=True
        print(f"Is query {i} fraudulent? {b_t}. Likelyhood of fraud: {p}")
        time.sleep(0.5)
        if stop_print:
            print("")
            time.sleep(1)
        i+=1

def _shutdown(_signum, _frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    if DECRYPTION_KEY_PATH:
        print("Key path set; fetching decryption key from Trustee")
        fetch_secret_trustee(DECRYPTION_KEY_PATH, DECRYPTION_KEY_OUTPUT)
        print(f"Downloading blob: {CONTAINER_NAME}/{BLOB_NAME}")
        download_blob(AZURE_STORAGE_NAME, BLOB_NAME, CONTAINER_NAME)
    else:
        print("No DECRYPTION_KEY_PATH; using default dataset")
        add_default_dataset()

    print("Loading data from folder")
    data = open_all_files_in_folder(DATASET_LOCATION)
    inspect_data(data)

    print("Done processing data, sleeping...")
    while True:
        sleep(5)

if __name__ == "__main__":
    main()
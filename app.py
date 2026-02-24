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

# SAS token path. This is a mounted (sealed) secret volume.
# Example: /azure/azure-sas
SAS_TOKEN_PATH = os.getenv("SAS_TOKEN_PATH", "")
default_sas_token = "c3A9ciZzdD0yMDI1LTEwLTI3VDE1OjQyOjI3WiZzZT0yMDI4LTEwLTI3VDIyOjU3OjI3WiZzcHI9aHR0cHMmc3Y9MjAyNC0xMS0wNCZzcj1iJnNpZz12amFSb3RkN2RlJTJCM1F3bHpIVmFIRjJHVnllaHcxeGIzZkZpWGU5RTdZT0klM0Q="

# Azure storage name
AZURE_STORAGE_NAME = os.getenv("AZURE_STORAGE_NAME", "encrypteddatasets")

# Blob name
BLOB_NAME = os.getenv("BLOB_NAME", "dataset1.csv.enc")

# Container name
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "data")

# Threshold prediction
THRESHOLD_PREDICTION = os.getenv("TRESHOLD_PREDICTION", 0.999999)

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

def _head_n1(path, max_chars=20):
    """Read the first line of a file and return its first max_chars characters for display."""
    try:
        with open(path, "rb") as f:
            first_line = f.readline().decode("utf-8", errors="replace").strip()
        return (first_line[:max_chars] + ("..." if len(first_line) > max_chars else "")) or "(empty)"
    except Exception:
        return "(error)"


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
                "-kfile", DECRYPTION_KEY_PATH,
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
            print(f"  Found an encrypted file: {filename}")
            decrypt_file(file_path)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path) or filename.endswith('.enc'):
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

    if SAS_TOKEN_PATH == "":
        print("  No SAS token path set; using default SAS token")
        sas = base64.b64decode(default_sas_token).decode('utf-8')
    else:
        try:
            with open(SAS_TOKEN_PATH, 'r') as file:
                sas = file.read()
        except FileNotFoundError:
            print("  SAS token file not found")
        except Exception as e:
            print(f"  Error reading SAS token: {e}")

    if sas == 'NOT_FOUND' or sas == '':
        raise Exception("  ERROR: No SAS token found. SAS token path: '" + SAS_TOKEN_PATH + "'")

    blob_client = BlobClient.from_blob_url("https://" + storage_name + ".blob.core.windows.net/" + container_name + "/" + blob_name + "?" + sas)

    print(f"  Downloading Azure:///{storage_name}/{container_name}/{blob_name} -> {download_file_path}")
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
    print(f"#### Loaded {len(data)} transactions")
    print("#### Inspecting credit card transactions:")

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
        print("#### Decryption key path set; downloading encrypted blob")
        print(f"  Downloading blob: Azure:///{AZURE_STORAGE_NAME}/{CONTAINER_NAME}/{BLOB_NAME}")
        download_blob(AZURE_STORAGE_NAME, BLOB_NAME, CONTAINER_NAME)
    else:
        print("  No decryption key path set; using default plaintext dataset")
        add_default_dataset()

    print()
    print("#### Loading data from " + DATASET_LOCATION)
    data = open_all_files_in_folder(DATASET_LOCATION)
    inspect_data(data)

    print("#### Done processing data, sleeping...")
    while True:
        sleep(5)

if __name__ == "__main__":
    main()
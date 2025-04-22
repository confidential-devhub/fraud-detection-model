import numpy as np
import onnxruntime as rt
import pickle
import os
import csv
import time
from colorama import Fore, Style

# Load ONNX model
sess = rt.InferenceSession("setup/models/fraud/1/model.onnx", providers=rt.get_available_providers())

# Load scaler
with open('setup/artifact/scaler.pkl', 'rb') as handle:
    scaler = pickle.load(handle)

input_name = sess.get_inputs()[0].name
output_name = sess.get_outputs()[0].name

def ask_model(query):
    prediction = sess.run([output_name], {input_name: scaler.transform(query).astype(np.float32)})
    threshold = float(os.getenv("TRESHOLD_PREDICTION", 0.999999))
    bool_answer = np.squeeze(prediction) > threshold and np.squeeze(prediction) < 1
    perc_answer = "{:.5f}".format(100 * np.squeeze(prediction)) + "%"
    return (bool_answer, perc_answer)

def open_all_files_in_folder(folder_path):
    input_data = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    print(f"Loaded {file_path}")
                    reader = list(csv.reader(f))[1:]
                    input_data += reader
            except Exception as e:
                print(f"Could not read {filename}: {e}")

    # random.shuffle(input_data)
    return input_data

def main():
    data = open_all_files_in_folder("input/")

    print("Inspecting credit card transactions... (Note: printing the progress slows the process down)")

    i = 0
    for query in data:
        b, p = ask_model([query])
        b_t = "FALSE"
        stop_print=False
        if b:
            b_t = Fore.RED + "TRUE" + Style.RESET_ALL
            stop_print=True
        print(f"\rIs query {i} fraudulent? {b_t}. Likelyhood of fraud: {p}", end='')
        # time.sleep(0.3)
        if stop_print:
            print("")
            time.sleep(1)
        i+=1

if __name__ == "__main__":
    main()
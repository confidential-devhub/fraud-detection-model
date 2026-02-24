# fraud-detection-model

This is simply a containerized pre-built fraud-detection model described in[the official fraud detection guide](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_cloud_service/1/html-single/openshift_ai_tutorial_-_fraud_detection_example/index#training-a-model) and [the official fraud detection devel guide](https://developers.redhat.com/learning/learn:openshift:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx/resource/resources:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx-prerequisites-and-step-step-guide?source=sso).

```
podman build . -t fraud-detection
podman push fraud-detection your-registry/fraud-detection
```

The following environment variables are used by the application:

- **`DECRYPTION_KEY_PATH`**
  Path used to fetch the decryption key from the CDH key service. The `kbs:///` prefix is stripped and the remainder is requested from `http://127.0.0.1:8006/cdh/resource/<path>`. Default: empty (must be set for decryption).

- **`SAS_TOKEN_PATH`**
  Path to the file containing the Azure SAS token (e.g. a mounted sealed secret volume). Used when `SAS_TOKEN` is not set. Default: `/azure/azure-sas`.

- **`SAS_TOKEN`**
  Azure Blob Storage SAS token. If set, overrides reading from `SAS_TOKEN_PATH`. Default: empty.

- **`AZURE_STORAGE_NAME`**
  Azure storage account name used to build the blob URL. Default: `encrypteddatasets`.

- **`CONTAINER_NAME`**
  Azure blob container name. Default: `data`.

- **`BLOB_NAME`**
  Name of the encrypted blob to download (e.g. the CSV dataset). Default: `dataset1.csv.enc`.

- **`TRESHOLD_PREDICTION`**
  Score threshold above which a transaction is considered fraudulent (float between 0 and 1). Default: `0.999999`. (Note: env name has a typo “TRESHOLD”.)
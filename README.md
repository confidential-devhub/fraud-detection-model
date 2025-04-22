# fraud-detection-model

This is simply a containerized pre-built fraud-detection model described in[the official fraud detection guide](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_cloud_service/1/html-single/openshift_ai_tutorial_-_fraud_detection_example/index#training-a-model) and [the official fraud detection devel guide](https://developers.redhat.com/learning/learn:openshift:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx/resource/resources:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx-prerequisites-and-step-step-guide?source=sso).

Simply execute `setup/run.sh` and the model will be automatically created and packed in a container called `fraud-detection`.

```
./setup/run.sh
podman push fraud-detection your-registry/fraud-detection
```

Run with:
```
podman run --rm -v $(pwd)/input:/app/input:z -e TRESHOLD_PREDICTION=0.999999 your-requistry/fraud-detection
```
Set `TRESHOLD_PREDICTION` if you want to change the minimal likelyhood that triggers a fraud alert for each transaction inspected. Default is 0.999999.
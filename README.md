# fraud-detection-model

This is simply a containerized pre-built fraud-detection model described in https://developers.redhat.com/learning/learn:openshift:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx/resource/resources:building-and-evaluating-a-fraud-detection-model-with-tensorflow-and-onnx-prerequisites-and-step-step-guide?source=sso and available in https://github.com/redhat-developer-demos/openshift-ai.git.

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
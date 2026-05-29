# Model files

Prediction uses TensorFlow Lite / LiteRT model binaries for each crop:

- `backend/models/tomato_model.tflite`
- `backend/models/mango_model.tflite`
- `backend/models/coconut_model.tflite`

The JSON files in `backend/training/` are metadata. They are not enough for
prediction by themselves.

Prediction also requires class order metadata generated during training:

- `backend/training/class_names/tomato_classes.json`
- `backend/training/class_names/mango_classes.json`
- `backend/training/class_names/coconut_classes.json`

The class JSON order must match the TFLite output tensor order. Startup and
prediction validation fail with a descriptive error if `len(classes)` does not
match the model output size.

The app first looks for model files in `backend/models/`. You can also set
`MODEL_DIRS` to one or more directories that contain the files. Separate
multiple directories with `;` on Windows and `:` on Linux/macOS. Per-crop local
paths are also supported with `MODEL_PATH_TOMATO`, `MODEL_PATH_MANGO`, and
`MODEL_PATH_COCONUT`.

For deployment, use one of these options:

1. Commit the trained TFLite files in `backend/models/`.
2. Host the TFLite files somewhere durable and set `MODEL_BASE_URL` on Render.
   The backend will download:
   - `${MODEL_BASE_URL}/tomato_model.tflite`
   - `${MODEL_BASE_URL}/mango_model.tflite`
   - `${MODEL_BASE_URL}/coconut_model.tflite`
3. Or set per-crop URLs: `TOMATO_MODEL_URL`, `MANGO_MODEL_URL`,
   `COCONUT_MODEL_URL`.

Also set these required environment variables in the Render dashboard:

- `JWT_SECRET`
- `JWT_REFRESH_SECRET`
- `MONGO_URL`
- `FRONTEND_URL`

To audit model tensors and metadata class counts:

```powershell
cd backend
python audit_prediction_pipeline.py
```

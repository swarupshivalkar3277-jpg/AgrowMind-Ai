# Model files

Prediction needs trained model binaries for each crop:

- `backend/training/tomato_model.keras`
- `backend/training/mango_model.keras`
- `backend/training/coconut_model.keras`

The JSON files in `backend/training/` are only metadata. They are not enough for
TensorFlow prediction.

Prediction also requires class order metadata generated during training:

- `backend/training/class_names/tomato_classes.json`
- `backend/training/class_names/mango_classes.json`
- `backend/training/class_names/coconut_classes.json`

The class JSON order must match the final Dense layer order. Startup and
prediction validation fail with a descriptive error if `len(classes)` does not
match `model.output_shape[-1]`.

The app first looks for model files in `backend/training/`, `backend/ai/models/`,
and `backend/models/`. You can also set `MODEL_DIRS` to one or more directories
that contain the files. Separate multiple directories with `;` on Windows and
`:` on Linux/macOS.

For deployment, use one of these options:

1. Commit the trained files in `backend/training/`. The project `.gitignore`
   allows `backend/training/*_model.keras` and metadata JSON files.
2. Host the model files somewhere durable and set `MODEL_BASE_URL` on Render.
   The backend will download:
   - `${MODEL_BASE_URL}/tomato_model.keras`
   - `${MODEL_BASE_URL}/mango_model.keras`
   - `${MODEL_BASE_URL}/coconut_model.keras`
3. Or set per-crop URLs: `TOMATO_MODEL_URL`, `MANGO_MODEL_URL`,
   `COCONUT_MODEL_URL`.

Also set these required environment variables in the Render dashboard:

- `JWT_SECRET_KEY`
- `MONGO_URL`
- `FRONTEND_ORIGIN`

If a model was removed from git, retrain it with:

```powershell
cd backend
python train_model.py --crop tomato
python train_model.py --crop mango
python train_model.py --crop coconut
```

To audit dataset, model, and metadata class counts:

```powershell
cd backend
python audit_prediction_pipeline.py
```

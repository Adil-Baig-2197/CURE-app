FROM python:3.12-slim
WORKDIR /workspace
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY train_nhamcs.py ./train_nhamcs.py
ENTRYPOINT ["python", "train_nhamcs.py"]

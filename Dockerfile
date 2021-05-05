FROM python:3.7-slim
WORKDIR /g/project
ADD . /project
EXPOSE 5000
RUN pip install -r requirements.txt
CMD ["python","app.py"]
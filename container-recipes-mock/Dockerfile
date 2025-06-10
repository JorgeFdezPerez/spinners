FROM python:latest

# Default container configuration folder
ARG CONFIG_PATH="configuration"

# Copy python scripts for recipes server
COPY $CONFIG_PATH/*.py /home/

# upgrade pip version
RUN pip install --upgrade pip

# Install dependencies
RUN pip install asyncua
RUN pip install opcua
RUN pip install transitions
RUN pip install mysql-connector-python

# Run script on start
CMD [ "python", "/home/recipes_mock.py" ]
# Use the official Node-RED image as a base
FROM nodered/node-red:3.1

# Default container configuration folder
ARG CONFIG_PATH="configuration"

# Install additional Node-RED nodes or libraries globally
USER root
RUN npm install node-red-contrib-buffer-parser
RUN npm install node-red-contrib-modbus
RUN npm install node-red-contrib-opcua-server

# Switch back to the default user
USER node-red

# Copy your Node-RED settings and flows
COPY $CONFIG_PATH/settings.js /data/settings.js
COPY $CONFIG_PATH/flowsOPC.json /data/flows.json

# Expose node-RED default port
EXPOSE 1880
# Expose OPCUA server port
EXPOSE 54840
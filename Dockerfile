FROM freqtrade-tensorflow

# Switch user to root if you must install something from apt
# Don't forget to switch the user back below!
#USER root

#RUN apt-get update
#RUN apt install -y python3-pip python3-venv python3-dev python3-pandas git


# Install dependencies
# COPY requirements.txt /freqtrade/

# RUN pip install numpy --user --no-cache-dir \
#  && pip install -r requirements-dev.txt --user --no-cache-dir

COPY freqtradesignal.py /freqtrade/freqtrade/
COPY worker.py /freqtrade/freqtrade/

# The below dependency - pyti - serves as an example. Please use whatever you need!
#RUN pip install tensorflow

#RUN pip uninstall numpy -y
#RUN pip install numpy==1.21.2

# Empty the ENTRYPOINT to allow all commands
ENTRYPOINT []


# USER ftuser

if [ -d "../.venv" ]; then
    echo "Good job you knew how to create a python virtual enviornment."
else
    echo "I gotta create a virtual enviornment, give me a minute."
    
    python3 -m venv ../.venv
    source ../.venv/bin/activate

fi


echo "Installing requirements" 

pip install -r ../requirements.txt 

python3 ../app.py


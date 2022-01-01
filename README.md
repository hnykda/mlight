To test the mqtt handling layer:

In one terminal run:
```
sudo socat -d -d pty,raw,echo=0 pty,raw,echo=0
```

that spits two rows, the first one is address for the output, second one is address for the input, e.g.:
```
2022/01/01 20:59:31 socat[763121] N PTY is /dev/pts/9
2022/01/01 20:59:31 socat[763121] N PTY is /dev/pts/10
```

then allow access by e.g. `sudo chmod 777 /dev/pts/10`.

Then run the program in another terminal via:

```
poetry run python mlight/main.py --bus-address /dev/pts/10 --test
```

and then open in another terminal and read from the output (you probably need to run this as root):
```
cat < /dev/pts/9
```

and then send a message:

```
mosquitto_pub -h 192.168.0.202 -u mlight -P mlight  -t "mlight/1/1/set" -m '{"brightness": 50}'
```
and the read should print a dict with changes on the first
#!/bin/zsh
# shot.sh file.svg out.png width height — 3x screenshot via headless Chrome
svg=$1; out=$2; w=$3; h=$4
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --force-device-scale-factor=3 --window-size=$w,$h --default-background-color=00000000 --screenshot="$out" "file://$svg" >/dev/null 2>&1

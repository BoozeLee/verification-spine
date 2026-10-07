#!/bin/sh
i=0
while [ $i -lt 50000 ]; do printf "noise line %d padded out to make this big\n" $i; i=$((i+1)); done
sleep 60

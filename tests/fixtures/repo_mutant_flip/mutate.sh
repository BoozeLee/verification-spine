#!/bin/sh
# Break exactly the thing the claim is about.
sed -i 's/SUBJECT = "intact"/SUBJECT = "broken"/' subject.py

#!/bin/bash

if ! command -v pnpm &> /dev/null
then
    echo "pnpm could not be found, installing..."
    npm install -g pnpm
else
    echo "pnpm is already installed."
fi

echo "Running pnpm -h:"
pnpm -h

exit 0

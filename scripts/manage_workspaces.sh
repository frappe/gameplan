#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

disable_workspaces() {
    echo "Disabling workspaces..."
    if [ -f pnpm-workspace.yaml ]; then
        mv pnpm-workspace.yaml pnpm-workspace.yaml.disabled
        echo "Renamed pnpm-workspace.yaml to pnpm-workspace.yaml.disabled."
    elif [ -f pnpm-workspace.yaml.disabled ]; then
        echo "pnpm-workspace.yaml.disabled already exists. Workspaces might already be disabled."
    else
        echo "pnpm-workspace.yaml not found. Assuming workspaces are already disabled or file is misnamed."
    fi
    pnpm pkg set scripts.postinstall="npm run frontend_pnpm_install"
    echo "Root postinstall script restored to run frontend_pnpm_install."
    echo "Workspaces disabled."
}

enable_workspaces() {
    echo "Enabling workspaces..."
    pnpm pkg set scripts.postinstall="echo 'Root postinstall disabled as workspaces are active'"
    echo "Root postinstall script set to no-op for active workspaces."
    if [ -f pnpm-workspace.yaml.disabled ]; then
        mv pnpm-workspace.yaml.disabled pnpm-workspace.yaml
        echo "Renamed pnpm-workspace.yaml.disabled to pnpm-workspace.yaml."
    elif [ -f pnpm-workspace.yaml ]; then
        echo "pnpm-workspace.yaml already exists. Workspaces might already be enabled."
    else
        echo "pnpm-workspace.yaml.disabled not found. Cannot enable workspaces."
        exit 1
    fi
    echo "Removing old node_modules..."
    rm -rf node_modules ./frontend/node_modules/ frappe-ui/node_modules/
    echo "Running pnpm install..."
    pnpm install
    echo "Workspaces enabled and dependencies installed."
}


ACTION=$1
if [ "$ACTION" == "enable" ]; then
    enable_workspaces
elif [ "$ACTION" == "disable" ]; then
    disable_workspaces
else
    echo "Usage: $0 <enable|disable>"
    exit 1
fi

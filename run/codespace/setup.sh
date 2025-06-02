#!/bin/bash

export EXTENSIONS_GALLERY="$(cat <<EOF
{
  "nlsBaseUrl": "https://www.vscode-unpkg.net/_lp/",
  "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
  "itemUrl": "https://marketplace.visualstudio.com/items",
  "publisherUrl": "https://marketplace.visualstudio.com/publishers",
  "resourceUrlTemplate": "https://{publisher}.vscode-unpkg.net/{publisher}/{name}/{version}/{path}",
  "extensionUrlTemplate": "https://www.vscode-unpkg.net/_gallery/{publisher}/{name}/latest",
  "controlUrl": "https://main.vscode-cdn.net/extensions/marketplace.json"
}
EOF
)"

dpkg -i /tmp/code-server.deb

mkdir -p /io/code-cli-data /app/code-extensions
for ext in \
  "ms-ceintl.vscode-language-pack-zh-hans" \
  "ms-vscode.cmake-tools" \
  "qiu.llvm-ir-language-support" \
  "daohong-emilio.yash" \
  "mike-lischke.vscode-antlr4" \
  "twxs.cmake" \
  "RooVeterinaryInc.roo-cline" \
  "/tmp/cpptools-linux-x64.vsix"
do
  code-server \
    --user-data-dir /io/code-user-data \
    --extensions-dir /app/code-extensions \
    --install-extension $ext
done

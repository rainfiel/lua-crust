lua-crust
========
A gui based inspect tool for lua
--------

This project consists of two parts:

1. A wxPython powered application to connect/query/execute a lua vm
2. A simple lua socket server to embed to your lua vm

This project works for ejoy2dx(https://github.com/rainfiel/ejoy2dx), but it's easy to use it stand-alone, you can integrate the server to your lua vm. To do this, you may need:
* lsocket(https://github.com/rainfiel/lsocket)
* lua-crypt(https://github.com/cloudwu/lua-crypt)

You can find an example in ejoy2dx/project/example

* windows端口映射工具
用做gateway的windows版本需要在windows2008r2以上, 机器上需要预先做如下配置:
在拥有管理员权限的powershell命令行中执行下列命令
```
	winrm quickconfig
	y
	winrm set winrm/config/service/Auth '@{Basic="true"}'
	winrm set winrm/config/service '@{AllowUnencrypted="true"}'
	winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="1024"}'
```

* 使用方法

在s1上执行
./winpf --connectaddress 119.254.103.39 --connectport 10190 --listenport 10190 -g "gateway server ip" -u "gateway user" --password "gateway password"

TODO: 
* 多级gateway
    * 指定gateway服务器上的工具路径自动唤醒
* 端口映射失败后尝试自动更改端口

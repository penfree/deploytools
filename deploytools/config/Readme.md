# Config
Example:
```yaml
---
resources:    #定义所有的机器
    master0:  #resource name, 后面用这个名字引用resource
        hostname: hdpdev0.dev-bdmd.com        #主机名
        ip: 192.168.100.4                     #ip
    master1:
        hostname: hdpdev1.dev-bdmd.com
        ip: 192.168.100.5
    master2:
        hostname: hdpdev2.dev-bdmd.com
        ip: 192.168.100.6
resgroups:   #resource的分组
    master:  #分组名称,成员是保护的resource
        - master0
        - master1
        - master2
    slave:
        - master0
        - master1
        - master2
modules:   #所有待部署的模块
    module1:   #模块名称
        priority: 0    #优先级,默认为1000,
    module2:
        priority: 0    
        require:       #依赖的模块, 不能依赖比自己优先级低的模块, 比自己优先级高的模块没有必要写出来
            - module1
        resources:   #该模块需要部署的机器
            - master0
        resgroups:   #该模块需要部署的机器分组,  最终部署的机器是 resources和resgroups的并集
            - slave
        #除上述属性外的其他属性会被直接传递给模块的构造函数处理
```

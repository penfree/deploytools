# 安装k8s 1.7 HA Cluster

## 安装前准备
* linux版本： centos7.3
* 准备需要的docker镜像， 打包好的k8s.tar拷贝到所有机器上, 已准备好的文件在 ftp://192.168.95.2/k8s/k8s-1.9.3.tar.gz
```
# pull镜像，需要科学上网

# kuberentes basic components
docker pull gcr.io/google_containers/kube-apiserver-amd64:v1.9.3
docker pull gcr.io/google_containers/kube-proxy-amd64:v1.9.3
docker pull gcr.io/google_containers/kube-scheduler-amd64:v1.9.3
docker pull gcr.io/google_containers/kube-controller-manager-amd64:v1.9.3
docker pull gcr.io/google_containers/k8s-dns-sidecar-amd64:1.14.7
docker pull gcr.io/google_containers/k8s-dns-kube-dns-amd64:1.14.7
docker pull gcr.io/google_containers/k8s-dns-dnsmasq-nanny-amd64:1.14.7
docker pull gcr.io/google_containers/etcd-amd64:3.1.10
docker pull gcr.io/google_containers/pause-amd64:3.0

# kubernetes networks add ons
docker pull quay.io/coreos/flannel:v0.9.1-amd64
docker pull quay.io/calico/node:v3.0.3
docker pull quay.io/calico/kube-controllers:v2.0.1
docker pull quay.io/calico/cni:v2.0.1

# kubernetes dashboard
docker pull gcr.io/google_containers/kubernetes-dashboard-amd64:v1.8.3

# kubernetes heapster
docker pull gcr.io/google_containers/heapster-influxdb-amd64:v1.3.3
docker pull gcr.io/google_containers/heapster-grafana-amd64:v4.4.3
docker pull gcr.io/google_containers/heapster-amd64:v1.4.2

# kubernetes apiserver load balancer
docker pull nginx:latest

# 将镜像导出成一个包

docker save -o k8s.tar  gcr.io/google_containers/kube-apiserver-amd64:v1.9.3 gcr.io/google_containers/kube-proxy-amd64:v1.9.3 gcr.io/google_containers/kube-scheduler-amd64:v1.9.3 \
 gcr.io/google_containers/kube-controller-manager-amd64:v1.9.3  gcr.io/google_containers/k8s-dns-sidecar-amd64:1.14.7  gcr.io/google_containers/k8s-dns-kube-dns-amd64:1.14.7 \
 gcr.io/google_containers/k8s-dns-dnsmasq-nanny-amd64:1.14.7  gcr.io/google_containers/etcd-amd64:3.1.10  gcr.io/google_containers/pause-amd64:3.0 \
 quay.io/coreos/flannel:v0.9.1-amd64  quay.io/calico/node:v3.0.3  quay.io/calico/kube-controllers:v2.0.1  quay.io/calico/cni:v2.0.1 \
 gcr.io/google_containers/kubernetes-dashboard-amd64:v1.8.3 gcr.io/google_containers/heapster-influxdb-amd64:v1.3.3 \
 gcr.io/google_containers/heapster-grafana-amd64:v4.4.3  gcr.io/google_containers/heapster-amd64:v1.4.2  nginx:latest

```

* 准备配置文件
```yaml
--
k8s:
  dockerVersion: 1.12.6
  k8sVersion: 1.7.5
  imagePath: /root/k8s.tar
  master1: 
    ip: 192.168.100.18
    hostname: hdp0.dev-bdmd.com
  master2: 
    ip: 192.168.100.22
    hostname: hdp1.dev-bdmd.com
  master3: 
    ip: 192.168.100.23
    hostname: hdp2.dev-bdmd.com
  podSubnet: 10.244.0.0/16
  virtualIP: 192.168.100.220
  slaves: []
ssh:
  user: root
  identityFile: /root/.ssh/hadoop-dev.key
  password: ''
```

## 配置文件生成及分发

* 同步集群时间，时间差别大可能会导致从外部访问apiserver失败
* 执行preinstall.py --config config.yaml， 完成以下操作
  * 配置yum repo
  * 关闭防火墙
  * 关闭selinux
  * 安装docker, kubelet, kubeadm
  * 导入docker镜像
* 重启所有机器, 如果不重启可能会有路由问题，主要是由于关闭防火墙导致的
* 安装etcd
  * 执行deployetcd.py --config config.yaml, 完成ETCD的部署，执行完成后在3个master上手动检查etcd安装状态
```
docker exec -it etcd ash

# 三个节点都在切都是healthy则正常
etcdctl member list
etcdctl cluster-health
```
  * 如果需要重新安装，需要删除etcd数据， 在3个master上 rm -rf /var/lib/etcdcluster/
* 使用kubeadm初始化master
  * 执行deploymaster1-step1.py， 完成master1初始化. 
  * 等待container初始化完成, 除了kube-dns外，其他都是running
```
[root@s1 ~]# kubectl get po  --all-namespaces
NAMESPACE     NAME                                           READY     STATUS    RESTARTS   AGE
kube-system   kube-apiserver-s1.yuhuatai-bdmd.com            1/1       Running   0          14s
kube-system   kube-controller-manager-s1.yuhuatai-bdmd.com   1/1       Running   1          28s
kube-system   kube-dns-2425271678-625th                      0/3       Pending   0          1m
kube-system   kube-proxy-d61ck                               1/1       Running   0          1m
kube-system   kube-scheduler-s1.yuhuatai-bdmd.com            1/1       Running   1          27s
```
  * 执行deploymaster1-step2.py, 完成flannel的安装。
    * 执行完成后在master1上执行kubectl get pods --all-namespaces -o wide等待所有pods状态为running
```

[root@s1 ~]# kubectl get po  --all-namespaces -w
NAMESPACE     NAME                                           READY     STATUS    RESTARTS   AGE
kube-system   kube-apiserver-s1.yuhuatai-bdmd.com            1/1       Running   0          2m
kube-system   kube-controller-manager-s1.yuhuatai-bdmd.com   1/1       Running   1          2m
kube-system   kube-dns-2425271678-625th                      3/3       Running   0          3m
kube-system   kube-flannel-ds-4s9nx                          2/2       Running   0          1m
kube-system   kube-proxy-d61ck                               1/1       Running   0          3m
kube-system   kube-scheduler-s1.yuhuatai-bdmd.com            1/1       Running   1          2m
```

   * 这里如果出现kube-dns访问不到apiserver的情况需要考虑两个可能
      * 防火墙是否已经关闭， 在宿主机能不能访问
      * iptables路由问题，刷新路由
```
systemctl stop kubelet
systemctl stop docker
iptables --flush
iptables -tnat --flush
systemctl start kubelet
systemctl start docker
```
  * 执行deploymaster1-step3.py, 完成dashboard、heapster的安装, 之后进行以下检查
    * 在master1上执行"kubectl proxy --address='0.0.0.0' &" 启动proxy，即可在本地访问dashboard  "http://master1:30000"
    * 在master1上检查所有pods是否都正常
    * 在dashboard上查看Pods的CPU以及Memory信息是否正常呈现
  * 执行setupha-step1.py, 配置master集群高可用, 完成后进行以下检查
    * 在master2, master3上执行 kubectl get nodes -o wide 查看节点是否都加进来了
  * 执行setupha-step2.py, 修改配置
  * 验证高可用配置成功
    * 在k8s-master1、k8s-master2、k8s-master3任意节点上检测服务启动情况，发现apiserver、controller-manager、kube-scheduler、proxy、flannel已经在k8s-master1、k8s-master2、k8s-master3成功启动
```
$ kubectl get pod --all-namespaces -o wide | grep k8s-master2
kube-system   kube-apiserver-k8s-master2              1/1       Running   1          55s       192.168.60.72   k8s-master2
kube-system   kube-controller-manager-k8s-master2     1/1       Running   2          18m       192.168.60.72   k8s-master2
kube-system   kube-flannel-ds-t8gkh                   2/2       Running   4          18m       192.168.60.72   k8s-master2
kube-system   kube-proxy-bpgqw                        1/1       Running   1          18m       192.168.60.72   k8s-master2
kube-system   kube-scheduler-k8s-master2              1/1       Running   2          18m       192.168.60.72   k8s-master2

$ kubectl get pod --all-namespaces -o wide | grep k8s-master3
kube-system   kube-apiserver-k8s-master3              1/1       Running   1          1m        192.168.60.73   k8s-master3
kube-system   kube-controller-manager-k8s-master3     1/1       Running   2          18m       192.168.60.73   k8s-master3
kube-system   kube-flannel-ds-tmqmx                   2/2       Running   4          18m       192.168.60.73   k8s-master3
kube-system   kube-proxy-4stg3                        1/1       Running   1          18m       192.168.60.73   k8s-master3
kube-system   kube-scheduler-k8s-master3              1/1       Running   2          18m       192.168.60.73   k8s-master3
```

   * 在k8s-master1、k8s-master2、k8s-master3任意节点上通过kubectl logs检查各个controller-manager和scheduler的leader election结果，可以发现只有一个节点有效表示选举正常

```
$ kubectl logs -n kube-system kube-controller-manager-k8s-master1
$ kubectl logs -n kube-system kube-controller-manager-k8s-master2
$ kubectl logs -n kube-system kube-controller-manager-k8s-master3

$ kubectl logs -n kube-system kube-scheduler-k8s-master1
$ kubectl logs -n kube-system kube-scheduler-k8s-master2
$ kubectl logs -n kube-system kube-scheduler-k8s-master3
```

   * 在k8s-master1、k8s-master2、k8s-master3任意节点上查看deployment的情况

```
$ kubectl get deploy --all-namespaces
NAMESPACE     NAME                   DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kube-system   heapster               1         1         1            1           41m
kube-system   kube-dns               1         1         1            1           48m
kube-system   kubernetes-dashboard   1         1         1            1           43m
kube-system   monitoring-grafana     1         1         1            1           41m
kube-system   monitoring-influxdb    1         1         1            1           41m
```

  * 执行setupha-step3.py， 配置keepalived, 配置完成后 ping virtualIP检测是否成功
  * 执行setupha-step4.py, 配置nginx负载均衡
    * 完成后执行 curl -L virtualIP:8443 并查看keepalived日志确认虚拟ip指向
  * 在k8s-master1上设置kube-proxy使用keepalived的虚拟IP地址，避免k8s-master1异常的时候所有节点的kube-proxy连接不上
    * kubectl edit -n kube-system configmap/kube-proxy  修改为'server: https://virtualIP:8443'
    * 在master1上删除所有kube-proxy重建
    * 在3个master上重启docker kubelet keepalived
    * 在master1上检查各个节点pod的启动状态，每个master上都成功启动heapster、kube-apiserver、kube-controller-manager、kube-dns、kube-flannel、kube-proxy、kube-scheduler、kubernetes-dashboard、monitoring-grafana、monitoring-influxdb。并且所有pod都处于Running状态表示正常
  * 执行joinslave.py 将slave加入集群，可以指定--slave添加指定节点
    * 执行kubectl get nodes检查是否加入成功

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
  imagePath: /root/k8s.tar.gz
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
  * 关闭selinux
  * 安装docker, kubelet, kubeadm
  * 导入docker镜像
* 重启所有机器
* 执行deployetcd.py --config config.yaml, 部署ETCD, 然后手动验证etcd部署正确
```
$ docker exec -ti etcd etcdctl cluster-health
member 531504c79088f553 is healthy: got healthy result from http://192.168.20.29:2379
member 56c53113d5e1cfa3 is healthy: got healthy result from http://192.168.20.27:2379
member 7026e604579e4d64 is healthy: got healthy result from http://192.168.20.28:2379
cluster is healthy

$ docker exec -ti etcd etcdctl member list
531504c79088f553: name=etcd3 peerURLs=http://192.168.20.29:2380 clientURLs=http://192.168.20.29:2379,http://192.168.20.29:4001 isLeader=false
56c53113d5e1cfa3: name=etcd1 peerURLs=http://192.168.20.27:2380 clientURLs=http://192.168.20.27:2379,http://192.168.20.27:4001 isLeader=false
7026e604579e4d64: name=etcd2 peerURLs=http://192.168.20.28:2380 clientURLs=http://192.168.20.28:2379,http://192.168.20.28:4001 isLeader=true
```
* 使用kubeadm初始化master
  * 执行deploymaster1-step1.py， 完成master1初始化. 等待所有pods都是running
  * 要记住这里输出的kubeadm join --token TOKEN --discovery-token-ca-cert-hash TOKENHASH, 将token和tokenHash补充到配置文件中
```
[root@s1 ~]# kubectl get po  --all-namespaces
NAMESPACE     NAME                                           READY     STATUS    RESTARTS   AGE
kube-system   kube-apiserver-s1.yuhuatai-bdmd.com            1/1       Running   0          14s
kube-system   kube-controller-manager-s1.yuhuatai-bdmd.com   1/1       Running   1          28s
kube-system   kube-dns-2425271678-625th                      0/3       Pending   0          1m
kube-system   kube-proxy-d61ck                               1/1       Running   0          1m
kube-system   kube-scheduler-s1.yuhuatai-bdmd.com            1/1       Running   1          27s
```
  * 执行deploymaster-step2.py, 完成dashboard, heapster的部署
    * 执行完成后在master1上执行kubectl get pods --all-namespaces -o wide等待所有pods状态为running
    * 访问https://master1:30000可以看到dashboard的界面
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
  * 执行setupha-step1.py 部署master2, master3
    * 等待所有pod都处于running状态
    * ping virtualIP, 检查keepalived配置是否成功
    * curl -k https://virtualip:16443 检查负载均衡是否成功
  * 在master1上设置proxy高可用，设置server指向高可用虚拟IP以及负载均衡的16443端口
  ```
  kubectl edit -n kube-system configmap/kube-proxy
        server: https://192.168.20.10:16443
  ```
  * 在master1上重启proxy
  ```
  $ kubectl get pods --all-namespaces -o wide | grep proxy

  $ kubectl delete pod -n kube-system kube-proxy-XXX
  ```
  * 加入slave节点
    * py joinslave.py --config config/test.yaml --slave slaveip --init
    * 如果slave节点之前已经在配置文件中配置过, 则不需要指定--slave和--init, 配置文件中的slave节点会自动加入
    * 如果是一个新增节点,则需要先进行机器初始化 然后加--init选项
  


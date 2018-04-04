package main

import (
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"os"
	"path"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/mitchellh/go-homedir"

	log "github.com/Sirupsen/logrus"
	winrm "github.com/masterzen/winrm"
	colorable "github.com/mattn/go-colorable"
	terminal "golang.org/x/crypto/ssh/terminal"
	cli "gopkg.in/urfave/cli.v1"
)

//程序初始化
func initProgram() {
	pid := fmt.Sprint(os.Getpid())
	tmpDir, _ := homedir.Dir()
	if err := isProcExist(tmpDir); err == nil {
		pidFile, _ := os.Create(path.Join(tmpDir, ".winpf.pid"))
		defer pidFile.Close()
		pidFile.WriteString(pid)
	} else {
		os.Exit(1)
	}
}

// 判断进程是否启动
func isProcExist(tmpDir string) (err error) {
	pidFile, err := os.Open(path.Join(tmpDir, ".winpf.pid"))
	defer pidFile.Close()
	if err == nil {
		filePid, err := ioutil.ReadAll(pidFile)
		if err == nil {
			pidStr := fmt.Sprintf("%s", filePid)
			pid, _ := strconv.Atoi(pidStr)
			_, err := os.FindProcess(pid)
			if err == nil {
				fmt.Printf("Program is already running, Pid:%s\n", pidStr)
				return errors.New("Program is already running")
			}

		}
	}
	return nil
}

func readPassword(tip string) string {

	fmt.Print(tip)
	bytePassword, err := terminal.ReadPassword(int(syscall.Stdin))
	if err != nil {
		panic(err)
	}
	password := string(bytePassword)

	return strings.TrimSpace(password)
}

func main() {
	initProgram()
	log.SetFormatter(&log.TextFormatter{ForceColors: true})
	if runtime.GOOS == "linux" {
		file, err := os.OpenFile("/var/log/winpf.log", os.O_APPEND|os.O_CREATE, 0666)
		if err == nil {
			log.SetOutput(file)
		} else {
			log.SetOutput(colorable.NewColorableStdout())
			log.Warnf("Failed to log to file, using default stderr")
		}
	} else {
		log.SetOutput(colorable.NewColorableStdout())
	}
	// Create cli application
	var cliApp = cli.NewApp()
	cliApp.Name = "Windows pf tool"
	cliApp.Flags = []cli.Flag{
		cli.StringFlag{
			Name:  "connectaddress",
			Value: "119.254.103.39",
			Usage: "The target address",
		},
		cli.IntFlag{
			Name:  "connectport",
			Value: 10190,
			Usage: "The target port",
		},
		cli.IntFlag{
			Name:  "listenport",
			Value: 10190,
			Usage: "listenport on gateway windows server",
		},
		cli.StringFlag{
			Name:  "gateway, g",
			Usage: "The gateway windows server",
		},
		cli.BoolFlag{
			Name:  "force, f",
			Usage: "Force replace portforward",
		},
		cli.IntFlag{
			Name:  "gatewayport, p",
			Value: 5985,
			Usage: "winrm management port on gateway server",
		},
		cli.StringFlag{
			Name:  "user, u",
			Value: "Administrator",
			Usage: "User of gateway server",
		},
		cli.StringFlag{
			Name:  "logfile",
			Value: "pf.log",
			Usage: "Log file name",
		},
		cli.StringFlag{
			Name:  "password",
			Usage: "Password of gateway server",
		},
	}
	cliApp.Action = portforward
	// Run
	cliApp.Run(os.Args)
}

//NewWinrmClient 获取一个winrm的Client
func NewWinrmClient(host string, port int, user, password string) (*winrm.Client, error) {
	endpoint := winrm.NewEndpoint(host, port, false, false, nil, nil, nil, 0)
	client, err := winrm.NewClient(endpoint, user, password)
	if err != nil {
		panic(err)
	}
	return client, err
}

// 检查端口是否打开
func checkPort(host string, port int) bool {
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, strconv.Itoa(port)), 2*time.Second)
	if err != nil {
		log.Infof("%v", err)
		//log.Infof("Port %d is not in use", port)
		return false
	}
	conn.Close()
	//log.Errorf("Port %d is already in use\n", port)
	return true
}

// 在远程服务器上检查端口是否打开
func remoteCheckPort(client *winrm.Client, host string, port int) bool {
	cmd := winrm.Powershell("New-Object System.Net.Sockets.TCPClient -ArgumentList " + host + "," + strconv.Itoa(port))
	stdout, stderr, exitCode, err := client.RunWithString(cmd, "")
	if err != nil || exitCode != 0 {
		log.Errorf("stdout:%v, stderr:%v, exitCode:%v", stdout, stderr, exitCode)
		return false
	}
	return true
}

// 建立端口映射
// client: winrm客户端
// gatewayAddress: gateway服务器地址
// targetAddress: 目标地址
// targetPort: 目标端口
// listenAddress: 本机绑定的地址，''表示绑定到所有地址
// listenPort: 本机绑定的端口， 0 表示和目标端口一致
// force: 强制重置当前端口映射
func ensurePortForward(client *winrm.Client, gatewayAddress, targetAddress string, targetPort int, listenPort int, force bool) error {
	if listenPort == 0 {
		listenPort = targetPort
	}
	// 检查listenPort是否已经打开，已打开则假设端口映射已经成功建立
	pfExisted := checkPort(gatewayAddress, listenPort)
	if !force && pfExisted {
		return nil
	}

	// 删除已经存在的端口映射
	if pfExisted {
		_, _, _, err := client.RunWithString("netsh interface portproxy delete v4tov4 listenport="+strconv.Itoa(listenPort), "")
		if err != nil {
			log.Errorf("Delete old portforward failed\n")
			return err
		}
		log.Infoln("Delete old portforward success")
	}

	// 重新添加端口映射
	stdout, stderr, _, err := client.RunWithString("netsh interface portproxy add v4tov4 connectaddress="+targetAddress+" connectport="+strconv.Itoa(targetPort)+" listenport="+strconv.Itoa(listenPort), "")
	if err != nil {
		log.Errorf("Create port forward failed, %v, stdout:\n%s\n, stderr:\n%s\n", err, stdout, stderr)
		return err
	}

	// 测试端口映射建立是否成功
	succ := checkPort(gatewayAddress, listenPort)
	if succ {
		log.Infoln("Set portforward success")
	} else {
		log.Warnln("Port is not open, portforward may be failed")
	}
	return nil
}

func allowPort(client *winrm.Client, port int) error {
	//在远程服务器上添加防火墙规则
	_, stderr, _, err := client.RunWithString("netsh advfirewall firewall add rule name=\"bigdata\" dir=in action=allow protocol=TCP localport="+strconv.Itoa(port), "")
	if err != nil {
		log.Errorf("Create firewall rule failed, msg[%s]", stderr)
	}
	return err
}

//portforward 在远程服务器上建立端口映射
func portforward(c *cli.Context) error {
	password := c.String("password")
	if len(password) == 0 {
		password = readPassword("Gateway Password:")
	}
	client, _ := NewWinrmClient(c.String("gateway"), c.Int("gatewayport"), c.String("user"), password)
	// 在远程服务器的防火墙上允许开放端口
	err := allowPort(client, c.Int("listenport"))
	if err != nil {
		panic(err)
	}
	checkCount := 0
	for {
		// 检查要连接的端口是否可以访问
		isConnectPortOpen := remoteCheckPort(client, c.String("connectaddress"), c.Int("connectport"))
		if !isConnectPortOpen {
			log.Errorf("Cannot connect to %s:%d", c.String("connectaddress"), c.Int("connectport"))
			time.Sleep(3 * time.Second)
			continue
		}
		checkCount++
		force := false
		if c.Bool("force") && checkCount == 1 {
			force = true
		}
		isOpen := checkPort(c.String("gateway"), c.Int("listenport"))
		if !force && isOpen {
			time.Sleep(30 * time.Second)
			if checkCount%100 == 0 {
				log.Infof("Has checked %d times", checkCount)
			}
			continue
		}
		if !isOpen {
			log.Infof("Port not open, trying to build")
		} else {
			log.Infof("Force replace port forward")
		}
		err := ensurePortForward(client, c.String("gateway"), c.String("connectaddress"), c.Int("connectport"), c.Int("listenport"), force)
		if err != nil {
			log.Errorf("%v\n", err)
			continue
		}
	}
}

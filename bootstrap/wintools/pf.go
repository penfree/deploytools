package main

import (
	"fmt"
	"io/ioutil"
	"net"
	"os"
	"os/exec"
	"strconv"
	"strings"

	log "github.com/Sirupsen/logrus"
	colorable "github.com/mattn/go-colorable"
	cli "gopkg.in/urfave/cli.v1"
)

// 执行命令
func runCmd(args ...string) ([]byte, error) {
	removeUTF8BOM := func(b []byte) []byte {
		if len(b) >= 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF {
			return b[3:]
		}
		return b
	}
	f, err := ioutil.TempFile("", "netcmd")
	if err != nil {
		return nil, err
	}
	f.Close()
	defer os.Remove(f.Name())
	cmd := fmt.Sprintf(`%s | Out-File "%s" -encoding UTF8`, strings.Join(args, " "), f.Name())
	out, err := exec.Command("powershell", "-Command", cmd).CombinedOutput()
	if err != nil {
		if len(out) != 0 {
			return nil, fmt.Errorf("%s failed: %v: %q", args[0], err, string(removeUTF8BOM(out)))
		}
		var err2 error
		out, err2 = ioutil.ReadFile(f.Name())
		if err2 != nil {
			return nil, err2
		}
		if len(out) != 0 {
			return nil, fmt.Errorf("%s failed: %v: %q", args[0], err, string(removeUTF8BOM(out)))
		}
		return nil, fmt.Errorf("%s failed: %v", args[0], err)
	}
	out, err = ioutil.ReadFile(f.Name())
	if err != nil {
		return nil, err
	}
	return removeUTF8BOM(out), nil
}

// 建立端口映射
// targetAddress: 目标地址
// targetPort: 目标端口
// listenAddress: 本机绑定的地址，''表示绑定到所有地址
// listenPort: 本机绑定的端口， 0 表示和目标端口一致
// force: 强制重置当前端口映射
func ensurePortForward(targetAddress string, targetPort int, listenPort int, force bool) error {
	if listenPort == 0 {
		listenPort = targetPort
	}
	// 检查listenPort是否已经打开，已打开则假设端口映射已经成功建立
	pfExisted := false
	conn, err := net.DialTimeout("tcp", net.JoinHostPort("", strconv.Itoa(listenPort)), 3)
	if conn != nil {
		conn.Close()
		pfExisted = true
		log.Errorf("Port %d is already in use\n", listenPort)
		if !force {
			return nil
		}
	} else {
		log.Infof("Port %d is not in use", listenPort)
	}

	// 删除已经存在的端口映射
	if pfExisted {
		_, err := runCmd("netsh", "interface", "portproxy", "delete", "v4tov4", "listenport="+strconv.Itoa(listenPort))
		if err != nil {
			log.Errorf("Delete old portforward failed\n")
			os.Exit(1)
		}
		log.Infoln("Delete old portforward success")
	}

	// 重新添加端口映射
	_, err = runCmd("netsh", "interface", "portproxy", "add", "v4tov4", "connectaddress="+targetAddress, "connectport="+strconv.Itoa(targetPort), "listenport="+strconv.Itoa(listenPort))
	if err != nil {
		log.Errorf("Create port forward failed, %v", err)
		return err
	}

	// 测试端口映射建立是否成功
	conn, err = net.DialTimeout("tcp", net.JoinHostPort("", strconv.Itoa(listenPort)), 3)
	if conn != nil {
		conn.Close()
		log.Infoln("Set portforward success")
	} else {
		log.Warnln("Port is not open, portforward may by failed")
	}
	return nil
}

func main() {
	log.SetFormatter(&log.TextFormatter{ForceColors: true})
	log.SetOutput(colorable.NewColorableStdout())
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
			Value: 21019,
			Usage: "The target port",
		},
		cli.IntFlag{
			Name:  "listenport",
			Value: 21019,
			Usage: "The target port",
		},
		cli.BoolFlag{
			Name:  "force",
			Usage: "Force reset portforward",
		},
	}
	cliApp.Action = portforward
	// Run
	cliApp.Run(os.Args)
}

func portforward(c *cli.Context) error {
	err := ensurePortForward(c.String("connectaddress"), c.Int("connectport"), c.Int("listenport"), c.Bool("force"))
	if err != nil {
		log.Errorf("%v\n", err)
		os.Exit(1)
	}
	return nil
}

func routeAdmin(c *cli.Context) error {
	return nil
}

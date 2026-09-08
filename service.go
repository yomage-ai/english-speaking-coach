package main

import (
	"bytes"
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func fetchJSON(address string) M {
	u, e := url.Parse(address)
	must(e)
	require(u.Scheme == "http" && (u.Hostname() == "127.0.0.1" || u.Hostname() == "localhost") && u.User == nil, "Only loopback HTTP is allowed")
	client := &http.Client{Timeout: 2 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return fmt.Errorf("Redirects are not allowed") }}
	r, e := client.Get(address)
	must(e)
	defer r.Body.Close()
	require(r.StatusCode == 200, "Local service returned "+r.Status)
	var data M
	must(json.NewDecoder(r.Body).Decode(&data))
	return data
}
func checkService(base, root string, expected bool) M {
	u, e := url.Parse(base)
	must(e)
	require(u.Path == "" || u.Path == "/", "Service URL must be an origin")
	d := fetchJSON(strings.TrimRight(base, "/") + "/api/identity")
	require(d["application"] == "english-speaking-coach" && absolute(str(d["data_root"])) == absolute(root), "Port belongs to another service/archive; it was preserved")
	if expected {
		require(d["runtime"] == "go" && d["code_revision"] == revision && d["version"] == version, "Running service is an older build. Agent must verify its manager and active work before an explicit restart.")
	}
	fetchJSON(strings.TrimRight(base, "/") + "/api/overview")
	return d
}
func serviceReceipt() string { return filepath.Join(filepath.Dir(configPath()), "service.json") }
func xmlText(s string) string {
	var b bytes.Buffer
	must(xml.EscapeText(&b, []byte(s)))
	return b.String()
}
func runCommand(command string, args ...string) string {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	b, e := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if e != nil {
		panic(fmt.Errorf("%s failed: %s", filepath.Base(command), strings.TrimSpace(string(b))))
	}
	return strings.TrimSpace(string(b))
}
func freePort(port int) bool {
	l, e := net.Listen("tcp4", fmt.Sprintf("127.0.0.1:%d", port))
	if e != nil {
		return false
	}
	l.Close()
	return true
}
func serviceStart(root string, managed bool) M {
	root = absolute(root)
	base := "http://127.0.0.1:8897"
	var identity M
	err := attempt(func() { identity = fetchJSON(base + "/api/identity") })
	if err == nil {
		checkService(base, root, true)
		return M{"status": "reused", "url": base, "identity": identity, "manager": "existing"}
	}
	require(freePort(8897), "固定端口 8897 被其他实例占用；已保留占用者，请让 Agent 核对。")
	var out M
	withLock(filepath.Join(filepath.Dir(configPath()), ".service.lock"), func() {
		if attempt(func() { identity = fetchJSON(base + "/api/identity") }) == nil {
			checkService(base, root, true)
			out = M{"status": "reused", "url": base, "identity": identity}
			return
		}
		require(freePort(8897), "端口已被占用，未替换服务。")
		receipt := obj(maybeJSON(serviceReceipt(), M{}))
		require(len(receipt) == 0 || truth(receipt["stopped"]), "A registered service is unavailable. Agent must inspect its native manager before restarting; no second manager was created.")
		require(!truth(receipt["stopped"]), "服务由用户主动停止；需要明确 service resume 后再启动。")
		exe, e := os.Executable()
		must(e)
		exe = absolute(exe)
		args := []string{"serve", "--port", "8897", "--codex-home", codexHome(), "--skill-root", skillRoot()}
		binary := os.Getenv("ENGLISH_COACH_CODEX")
		if binary == "" {
			_ = attempt(func() { binary = codexExecutable() })
		}
		if binary != "" {
			args = append(args, "--codex-executable", absolute(binary))
		}
		if managed {
			args = append(args, "--workspace")
		} else {
			args = append(args, "--root", root)
		}
		id := "english-speaking-coach-" + hash([]byte(configPath()))[:12]
		directory := filepath.Join(filepath.Dir(configPath()), "service")
		mkdir(directory)
		logPath := filepath.Join(directory, "companion.log")
		manager := runtime.GOOS
		receipt = M{"manager": manager, "id": id, "url": base, "root": root, "executable": exe, "code_revision": revision, "log": logPath, "stopped": false, "persist": false}
		switch runtime.GOOS {
		case "darwin":
			uid := runCommand("/usr/bin/id", "-u")
			label := "local." + id
			plist := filepath.Join(directory, label+".plist")
			values := "<string>" + xmlText(exe) + "</string>"
			for _, a := range args {
				values += "<string>" + xmlText(a) + "</string>"
			}
			env := "<key>CODEX_HOME</key><string>" + xmlText(codexHome()) + "</string><key>ENGLISH_COACH_SKILL_ROOT</key><string>" + xmlText(skillRoot()) + "</string>"
			if c := os.Getenv("ENGLISH_COACH_CODEX"); c != "" {
				env += "<key>ENGLISH_COACH_CODEX</key><string>" + xmlText(c) + "</string>"
			}
			content := `<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>Label</key><string>` + label + `</string><key>ProgramArguments</key><array>` + values + `</array><key>EnvironmentVariables</key><dict>` + env + `</dict><key>RunAtLoad</key><true/><key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict><key>ThrottleInterval</key><integer>5</integer><key>StandardOutPath</key><string>` + xmlText(logPath) + `</string><key>StandardErrorPath</key><string>` + xmlText(logPath) + `</string></dict></plist>`
			atomicWrite(plist, []byte(content))
			runCommand("/bin/launchctl", "bootstrap", "gui/"+uid, plist)
			receipt["target"] = "gui/" + uid + "/" + label
			receipt["definition"] = plist
		case "linux":
			unit := id + ".service"
			cmdArgs := []string{"--user", "--unit", unit, "--property=Restart=on-failure", "--property=RestartSec=5s", "--property=StartLimitIntervalSec=60s", "--property=StartLimitBurst=3", "--setenv=CODEX_HOME=" + codexHome(), "--setenv=ENGLISH_COACH_SKILL_ROOT=" + skillRoot(), "--", exe}
			cmdArgs = append(cmdArgs, args...)
			runCommand("systemd-run", cmdArgs...)
			receipt["target"] = unit
			receipt["log"] = "journalctl --user -u " + unit
		case "windows":
			task := id
			definition := filepath.Join(directory, id+".xml")
			quoted := []string{}
			for _, a := range args {
				require(!strings.Contains(a, `"`), "Path has unsupported quote")
				quoted = append(quoted, `"`+a+`"`)
			}
			content := `<?xml version="1.0" encoding="UTF-16"?><Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Triggers/><Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>false</StartWhenAvailable><Enabled>true</Enabled><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure></Settings><Actions Context="Author"><Exec><Command>` + xmlText(exe) + `</Command><Arguments>` + xmlText(strings.Join(quoted, " ")) + `</Arguments><WorkingDirectory>` + xmlText(filepath.Dir(exe)) + `</WorkingDirectory></Exec></Actions></Task>`
			content = strings.Replace(content, `encoding="UTF-16"`, `encoding="UTF-8"`, 1)
			atomicWrite(definition, []byte(content))
			runCommand("schtasks.exe", "/Create", "/TN", task, "/XML", definition)
			runCommand("schtasks.exe", "/Run", "/TN", task)
			receipt["target"] = task
			receipt["definition"] = definition
		default:
			panic(fmt.Errorf("Unsupported service manager; Agent must use a verified native supervisor"))
		}
		writeJSON(serviceReceipt(), receipt)
		for i := 0; i < 40; i++ {
			if attempt(func() { identity = checkService(base, root, true) }) == nil {
				receipt["instance_id"] = identity["instance_id"]
				receipt["pid"] = identity["pid"]
				writeJSON(serviceReceipt(), receipt)
				out = merge(receipt, M{"status": "started", "identity": identity})
				return
			}
			time.Sleep(100 * time.Millisecond)
		}
		panic(fmt.Errorf("后台已交给系统管理器，但页面尚未通过检查；Agent 需要查看 %s", str(receipt["log"])))
	})
	return out
}
func serviceStop() {
	receipt := obj(readJSON(serviceReceipt()))
	base := str(receipt["url"])
	visible := fetchJSON(base + "/api/identity")
	expectedRoot := str(receipt["root"])
	if truth(visible["workspace_managed"]) {
		expectedRoot = str(workspace("")["data_root"])
	}
	identity := checkService(base, expectedRoot, false)
	require(identity["instance_id"] == receipt["instance_id"] && identity["executable"] == receipt["executable"], "服务实例身份已改变，未停止任何进程。")
	assertIdle(str(identity["data_root"]))
	switch receipt["manager"] {
	case "darwin":
		runCommand("/bin/launchctl", "bootout", str(receipt["target"]))
	case "linux":
		runCommand("systemctl", "--user", "stop", str(receipt["target"]))
	case "windows":
		runCommand("schtasks.exe", "/End", "/TN", str(receipt["target"]))
		runCommand("schtasks.exe", "/Delete", "/TN", str(receipt["target"]), "/F")
	default:
		panic("Unknown manager; nothing stopped")
	}
	receipt["stopped"] = true
	writeJSON(serviceReceipt(), receipt)
}

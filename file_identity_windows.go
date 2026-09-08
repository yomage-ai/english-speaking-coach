package main

import (
	"fmt"
	"golang.org/x/sys/windows"
	"os"
)

func fileIdentity(path string) string {
	f, e := os.Open(path)
	must(e)
	defer f.Close()
	var info windows.ByHandleFileInformation
	must(windows.GetFileInformationByHandle(windows.Handle(f.Fd()), &info))
	return fmt.Sprintf("%x:%x:%x", info.VolumeSerialNumber, info.FileIndexHigh, info.FileIndexLow)
}

//go:build darwin || linux

package main

import (
	"fmt"
	"os"
	"syscall"
)

func fileIdentity(path string) string {
	s, e := os.Stat(path)
	must(e)
	info := s.Sys().(*syscall.Stat_t)
	return fmt.Sprintf("%x:%x", info.Dev, info.Ino)
}

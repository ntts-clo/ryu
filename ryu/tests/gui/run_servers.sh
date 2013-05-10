#!/bin/bash
set -e

function run_servers() {
  echo "Run servers..."

  . $RYU_HOME/.venv/bin/activate
  $RYU_HOME/bin/ryu-manager --verbose --observe-links --noinstall-lldp-flow \
                            $RYU_HOME/ryu/topology/switches.py \
                            $RYU_HOME/ryu/app/rest_topology.py \
                            $RYU_HOME/ryu/app/ofctl_rest.py \
                            1>/dev/null 2>/dev/null &
  ryu_pid=$!
  echo "Ryu server's pid $ryu_pid"

  $RYU_HOME/ryu/gui/controller.py 1>/dev/null 2>/dev/null &
  gui_pid=$!
  echo "GUI server's pid $gui_pid"

  deactivate

  sudo $RYU_HOME/ryu/tests/gui/tools/mn_ctl.py 1>/dev/null 2>/dev/null &
  mn_pid=$!
  echo "Mininet controll server's pid $mn_pid"
}

function kill_servers() {
  echo "Kill servers..."

  kill $ryu_pid
  kill $gui_pid
  sudo kill $mn_pid

  echo "Done."
}

RYU_HOME=$(cd $(dirname $0) && cd ../../../ && pwd)

run_servers

trap "kill_servers" HUP INT QUIT TERM

wait

#!/bin/sh
set -eu

external_interface="${EXTERNAL_INTERFACE:-$(ip route show default | awk 'NR == 1 {print $5}')}"
test -n "$external_interface"

add_input_rule() {
    iptables -C INPUT "$@" 2>/dev/null || iptables -I INPUT 1 "$@"
}

# Host ports: SSH and Nginx only. UFW keeps the INPUT default policy at DROP;
# these idempotent rules make the intended access explicit.
add_input_rule -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
add_input_rule -i lo -j ACCEPT
add_input_rule -i "$external_interface" -p tcp --dport 22 -j ACCEPT
add_input_rule -i "$external_interface" -p tcp --dport 80 -j ACCEPT

# Docker performs DNAT before DOCKER-USER. Permit public Nginx and reject any
# future accidentally published container port on the external interface.
iptables -N AISUMMARY_DOCKER 2>/dev/null || true
iptables -F AISUMMARY_DOCKER
iptables -A AISUMMARY_DOCKER \
    -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A AISUMMARY_DOCKER \
    -i "$external_interface" -p tcp --dport 80 -j ACCEPT
iptables -A AISUMMARY_DOCKER -i "$external_interface" -j DROP
iptables -A AISUMMARY_DOCKER -j RETURN

iptables -C DOCKER-USER -j AISUMMARY_DOCKER 2>/dev/null ||
    iptables -I DOCKER-USER 1 -j AISUMMARY_DOCKER

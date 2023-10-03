#!/usr/bin/env bash

# Dependencies: whois, echo, read

checkDomain() {
  domain=$1
  whois "$domain" &>/dev/null
  if [[ $? -eq 0 ]]; then
    echo "$domain is already registered."
  else
    echo "$domain is available for registration."
  fi
}

read -p "Enter domain name: " domainToCheck
checkDomain "$domainToCheck"

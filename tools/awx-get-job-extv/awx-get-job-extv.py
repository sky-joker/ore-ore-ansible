#!/usr/bin/env python3
from getpass import getpass
import sys
import argparse
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def options():
    parser = argparse.ArgumentParser(prog="awx-get-job-extv.py",
                                     add_help=True,
                                     description="Get extra_vars from the job result executed with Ansible Tower(AWX).")

    parser.add_argument("--server", "-s",
                        type=str, required=True,
                        help="Specify IP or host name of Ansible Tower(AWX).")
    parser.add_argument("--user", "-u",
                        type=str, default="admin",
                        help="Specify Ansible Tower(AWX) user.")
    parser.add_argument("--password", "-p",
                        type=str,
                        help="Specify ANsible Tower(AWX) user password.")
    parser.add_argument("--job-id", "-id",
                        type=int, required=True,
                        help="Specify job id of get extra_vars.")
    parser.add_argument("--json-indent",
                        type=int,
                        help="Specify JSON indent number.")
    parser.add_argument("--ssl",
                        action="store_true",
                        help="Specify when using SSL connection.")
    parser.add_argument("--ssl-verify",
                        action="store_true",
                        help="Enable server certificate check.")

    args = parser.parse_args()
    if(not(args.password)):
        args.password = getpass()

    return args

def create_url(args):
    if(args.ssl):
        url = "https://%s/api/v1/jobs/" % args.server
    else:
        url = "http://%s/api/v1/jobs/" % args.server

    return url

def main():
    args = options()
    url = create_url(args)
    headers = {"Content-Type": "application/json"}

    try:
        ssl_verify = True if(args.ssl_verify) else False
        r = requests.get(url,
                         headers=headers,
                         auth=(args.user, args.password),
                         verify=ssl_verify)
    except Exception as e:
        print("Error: %s" % e)

    if(r.status_code == 200):
        for job in json.loads(r.text)["results"]:
            if(args.job_id == job["id"]):
                if(args.json_indent):
                    print(json.dumps(json.loads(job["extra_vars"]), indent=args.json_indent))
                    sys.exit(0)
                else:
                    print(job["extra_vars"])
                    sys.exit(0)
        print("job id %s not found." % args.job_id)
    else:
        print("Error: %s" % r.text)

if __name__ == "__main__":
    main()

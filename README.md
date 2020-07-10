# certificate-expiry-checker

Python script and cloudformation for a script to check certificates in ACM that are coming up to their expiry date.

### Use

* Check scripts for regions and change where needed (I'm in eu-west-1)
* Check vars.env and change where needed (S3 bucket name (to store code) and email addresses)
* Set STACK_NAME environment variable (ie: export STACK_NAME=certificate-expiry-checker)
* Run build.sh to build lambda function
* Run create-stack.sh to create cloudformation stack

Runs weekly based on cron setting in template - cron(0 15 ? * 5 *)

Checks certs in regions defined by variable REGIONS in lambda_function.py

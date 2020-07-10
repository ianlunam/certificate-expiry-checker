#!/bin/bash

set -euo pipefail

VARFILE=vars.env
source ${VARFILE}

cd "$(dirname "$0")"

STACK_NAME=${STACK_NAME:?}
TEMPLATE_PATH="./template.yaml"
if [[ ! -f ${VARFILE} ]]; then
    echo "Missing ${VARFILE} file"
    exit 1
fi

STACK_PARAMS="--parameters"
VARS=$(cat ${VARFILE} | egrep -v '^(#|$|STACK_NAME)')
while read line
do
    echo $line
    VAR=$(echo $line | awk -F\= '{print $1}')
    VAL=$(echo $line | awk -F\= '{print $2}')
    echo $VAR $VAL $STACK_PARAMS
    STACK_PARAMS="${STACK_PARAMS} ParameterKey=${VAR},ParameterValue=${VAL}"
done <<< "${VARS}"

echo STACK_PARAMS ${STACK_PARAMS}

stackUpdate() {
  echo "Updating Stack ${STACK_NAME} using template ${TEMPLATE_PATH}"
  CMD_OUT="$(aws cloudformation update-stack --region eu-west-1 --capabilities CAPABILITY_NAMED_IAM --stack-name "${STACK_NAME}" --template-body "file://$TEMPLATE_PATH" ${STACK_PARAMS} 2>&1 || true)"
  if echo "${CMD_OUT}" | grep "stackId"; then
    echo "${CMD_OUT}" | jq .
  else
    echo "${CMD_OUT}"
  fi
}

stackCreate() {
  CMD_OUT="$(aws cloudformation create-stack --region eu-west-1 --capabilities CAPABILITY_NAMED_IAM  --stack-name "${STACK_NAME}" --template-body "file://$TEMPLATE_PATH" ${STACK_PARAMS} 2>&1 || true)"
  if echo "${CMD_OUT}" | grep "AlreadyExistsException" 2>&1 > /dev/null; then
    stackUpdate
  else
    echo "Creating Stack ${STACK_NAME} using template ${TEMPLATE_PATH}"
    echo "${CMD_OUT}" | jq .
  fi
}

CMD_OUT=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region eu-west-1 2>/dev/null || true)

if [[ -z "${CMD_OUT}" ]]; then
    stackCreate
else
    stackUpdate
fi

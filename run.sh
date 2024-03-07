cd /opt/verjaardagskalender
docker stop verjaardagskalender
docker rm -f verjaardagskalender
docker run \
	--detach \
	--restart always \
	--env-file env.list \
	--name verjaardagskalender \
	--publish 8084:8084 \
	verjaardagskalender

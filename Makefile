TAG=stats_collector

docker:
	docker image build -t $(TAG) .

run: docker
	docker run -p 5000:5000 -d $(TAG)

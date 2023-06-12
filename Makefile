TAG=stats_collector

docker:
	docker image build -t $(TAG) .

run:
	docker run -p 5000:5000 -d $(TAG)

compose:
	docker compose up

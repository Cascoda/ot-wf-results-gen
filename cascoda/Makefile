MAKE = make

.DEFAULT_GOAL := run_all

run_all:
	$(MAKE) run_hdn
	$(MAKE) run_stats
	$(MAKE) run_report

run_hdn:
	poetry run python hdn_detector.py

run_stats:
	poetry run python extract_stats.py $(csv)

run_report:
	poetry run python generate_report.py $(csv)

run_hdn_single:
	poetry run python whitefield.py

clean:
	$(MAKE) clean_logs
	$(MAKE) clean_pcap_logs
	$(MAKE) clean_configs
	$(MAKE) clean_stats
	$(MAKE) clean_reports


cleanf:
	$(MAKE) cleanf_logs
	$(MAKE) cleanf_pcap_logs
	$(MAKE) cleanf_configs
	$(MAKE) clean_stats
	$(MAKE) clean_reports

clean_logs:
	rm -r ../logs/sim_runs*

cleanf_logs:
	rm -rf ../logs/sim_runs*

clean_configs:
	rm -r ../config/wf_ot_n*

cleanf_configs:
	rm -rf ../config/wf_ot_n*

clean_pcap_logs:
	rm -rf ../simulation_outputs/wf_ot_*

cleanf_pcap_logs:
	rm -rf ../simulation_outputs/wf_ot_*

clean_reports:
	rm -rf ../outputs/plots/*.png
	rm -rf ../outputs/*.pdf

clean_stats:
	rm -rf ../outputs/*.csv

## CHSH Game in Python Code

CHSH with 3-Phase voltage sources.  
Positive and negative sequence components as analogs for engtangled particles.  


## Usage
First, generate entagled particles  
`python generate_pairs.py -n 100 -o runs_out --freq 60 --ppc 1200 --mag 120 --seed 42`

Next, generate fair coin flips to determine the "questions" asked to Bob and Alice  
`python make_settings.py --runs 50 --out runs_out/settings.csv --seed 123`

Next, analyze as Bob or Alice  
`python chsh_analysis.py runs_out/alice_run*.csv --role alice --settings runs_out/settings.csv --a-deg 0 --a-prime-deg 45 -o alice_analysis`  
`python chsh_analysis.py runs_out/bob_run*.csv --role bob --settings runs_out/settings.csv --b-deg 22.5 --b-prime-deg 67.5 -o bob_analysis`  

Finally, aggregate results  
`python chsh_aggregate.py --alice alice_analysis/alice_outcomes.csv --bob bob_analysis/bob_outcomes.csv --out chsh_summary.csv`

OR, call the bash script that does everything for you
`bash run_chsh.sh`
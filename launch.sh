#!/usr/bin/env bash

SESSION="torcs"

tmux new-session -d -s $SESSION
tmux send-keys -t $SESSION "cd /torcs/gym_torcs" C-m
tmux send-keys -t $SESSION "python3 torcs_jm_par.py" C-m
tmux split-window -h -t $SESSION
tmux send-keys -t $SESSION "cd /torcs/torcs" C-m
tmux send-keys -t $SESSION "wine wtorcs.exe" C-m

tmux attach-session -t $SESSION

#!/usr/bin/env bash

SESSION="torcs"

tmux new-session -d -s $SESSION

players=$1
for ((i=1; i<=players; i++))
do
    tmux send-keys -t $SESSION "source venv/bin/activate" C-m
    tmux send-keys -t $SESSION "cd gym_torcs" C-m
    tmux send-keys -t $SESSION "python3 torcs_jm_par$i.py" C-m
    tmux split-window -h -t $SESSION
done

#tmux send-keys -t $SESSION "python3 torcs_jm_par.py" C-m
#tmux split-window -h -t $SESSION
tmux send-keys -t $SESSION "cd torcs" C-m
tmux send-keys -t $SESSION "sudo wine wtorcs.exe" C-m

tmux attach-session -t $SESSION
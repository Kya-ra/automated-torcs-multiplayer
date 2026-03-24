#!/usr/bin/env bash

set -e

SESSION="torcs"
players=$1
per_window=2

if [ -z "$players" ]; then
    echo "Usage: $0 <num_players>"
    exit 1
fi

tmux has-session -t $SESSION 2>/dev/null && tmux kill-session -t $SESSION
tmux new-session -d -s $SESSION -n "Players 1-$per_window"

player=1
window_index=0

while [ $player -le $players ]; do
    start=$player
    end=$((player + per_window - 1))
    [ $end -gt $players ] && end=$players

    window_name="Players $start-$end"

    if [ $window_index -eq 0 ]; then
        tmux rename-window -t $SESSION:0 "$window_name"
    else
        tmux new-window -t $SESSION -n "$window_name"
    fi

    current=$(tmux list-panes -t $SESSION:$window_index -F "#{pane_id}" | head -n1)

    for ((i=start; i<=end; i++)); do
        tmux send-keys -t $current "source venv/bin/activate" C-m
        tmux send-keys -t $current "cd gym_torcs" C-m
        tmux send-keys -t $current "python3 torcs_jm_par$i.py" C-m

        if [ $i -lt $end ]; then
            current=$(tmux split-window -t $current -P -F "#{pane_id}")
        fi
    done

    tmux select-layout -t $SESSION:$window_index tiled

    player=$((end + 1))
    window_index=$((window_index + 1))
done

#torcs is on its own
tmux new-window -t $SESSION -n "TORCS"
torcs_pane=$(tmux list-panes -t $SESSION:$window_index -F "#{pane_id}" | head -n1)

tmux send-keys -t $torcs_pane "cd torcs" C-m
tmux send-keys -t $torcs_pane "sudo wine wtorcs.exe" C-m

tmux attach-session -t $SESSION
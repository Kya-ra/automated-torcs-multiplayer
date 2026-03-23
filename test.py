from subprocess import call

player_count = input("Enter player count: ")
call(["./faststart.sh", str(player_count)])
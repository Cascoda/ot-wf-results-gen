#!/bin/bash

# CLI help
usage() {
    cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-n nNode] [-t vTime] [-s rSens] [-p nPosition] [-i iFilename] [-o oFilename]

Available options:
    -h      Print this help and exit
    -n      Change the number of nodes. Must be an integer.
    -t      Change the virtual simulation run time (minutes). Must be an integer.
    -s      Change the receive receive sensitivity of the nodes in dbm.
            Can either be a single numerical value (e.g. -99) which will set all rxSensitivity OR a list as with the format: "99 99 105".
    -x      Change the node position to a [x,y,z] vector. Must be provided if -n is used. Format: "[x,y,z] [x,y,z] [x,y,z] ..."
    -p      Changes the node ping size.
    -i      Input filename.
    -o      Output filename. Defaults to input filename.
EOF
  exit
}

# Define variables
unset nNode
unset vTime
unset rSens
unset nPosition
unset iFilename
unset oFilename

# Check CLI args
while getopts 'hn:t:s:x:p:i:o:' flag;
do
    case "$flag" in
        n ) nNode=$OPTARG;;
        t ) vTime=$OPTARG;;
        s ) rSens=$OPTARG;;
        x ) nPosition=$OPTARG;;
        p ) ping=$OPTARG;;
        i ) iFilename=$OPTARG;;
        o ) oFilename=$OPTARG;;
        h ) usage ;;
        \?) echo "Unknown option: -$OPTARG" >&2; usage >&2; exit 1;;
    esac
done

# Mandatory arugments
if [ -z ${iFilename+x} ]; then
    echo "ERROR: Input filename (-i) must be provided."
    echo
    usage >&2
    exit 1
fi

if  [ -n "$nNode" ] && [ -z ${nPosition+x} ]; then
    echo "ERROR: The number of nodes was changed but node positions were not set. Use both -n and -x together."
    echo
    usage >&2
    exit 1
fi

# Create new file
if [ -z ${oFilename+x} ]; then
    oFilename=$iFilename
    cp "$iFilename" "$iFilename".bak
else
    cp "$iFilename" "$oFilename"
fi

# Make changes
change_var() {
    var=$1
    replace=$1$2
    sed 's/^'"$var"'.*/'"$replace"'/' "$oFilename" > temp.cfg
    cp temp.cfg "$oFilename"
    rm temp.cfg
}

if [ -n "$nNode" ]; then
    change_var 'numOfNodes=' "$nNode"
fi

if [ -n "$vTime" ]; then
    change_var 'simulationEndTime=' "$vTime"
fi

if [ -n "$rSens" ]; then
    isNum='^[+-]?[0-9]+([.][0-9]+)?$'
    if ! [[ $rSens =~ $isNum ]] ; then
        read -ra sensArray <<< "$rSens"

        if [ ${#sensArray[@]} != "$nNode" ]; then #error handling rSens and no. nodes
            echo "ERROR: The number of nodes and number of receive sensitivities do not match."
            rm "$oFilename"
            exit 1
        fi

        for num in "${!sensArray[@]}"
        do
            change_var 'rxSensitivity\['"$num"']=' "${sensArray[$num]}"
        done
    else
        for i in $(seq $nNode);
        do
            num="$(($i-1))"
            change_var 'rxSensitivity\['"$num"']=' "$rSens"
        done
    fi
fi

if [ -n "$nPosition" ]; then
    read -ra posArray <<< "$nPosition" #turn cli arg into array
    if [ ${#posArray[@]} != "$nNode" ]; then #error handling positions and no. nodes
        echo "ERROR: The number of nodes and number of positions do not match."
        rm "$oFilename"
        exit 1
    fi

    lineNum=$(grep -n -m 1 'nodePosition' "$oFilename" | sed  's/\([0-9]*\).*/\1/') #get line num of first occurence of nodePosition
    sed '/nodePosition.*/d' "$oFilename" > temp.cfg #delete old node position data
    cp temp.cfg "$oFilename"
    rm temp.cfg
    for num in "${!posArray[@]}" #set new positions
    do
        pos=$(echo "${posArray[$num]}" | sed 's/[][]//g')
        nPositionList='nodePosition['"$num"']='"$pos"
        insertLineNum=$((lineNum+num))
        sed "$insertLineNum"'s/^/'"$nPositionList"'\n/' "$oFilename" > temp.cfg
        cp temp.cfg "$oFilename"
        rm temp.cfg
    done
fi

if [ -n "$ping" ]; then
    newPing='ping ff02::1 '$ping' 500 0.01 1;'
    change_var 'nodePing\[0]=' "$newPing"
    change_var 'nodePing\[2]=' "$newPing"
fi

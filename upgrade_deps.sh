#!/bin/bash

# Upgrades Protoc from https://github.com/protocolbuffers/protobuf/releases

black='\e[0;30m'
blackBold='\e[1;30m'
blackBackground='\e[1;40m'
red='\e[0;31m'
redBold='\e[1;31m'
redBackground='\e[0;41m'
green='\e[0;32m'
greenBold='\e[1;32m'
greenBackground='\e[0;42m'
yellow='\e[0;33m'
yellowBold='\e[1;33m'
yellowBackground='\e[0;43m'
blue='\e[0;34m'
blueBold='\e[1;34m'
blueBackground='\e[0;44m'
magenta='\e[0;35m'
magentaBold='\e[1;35m'
magentaBackground='\e[0;45m'
cyan='\e[0;36m'
cyanBold='\e[1;36m'
cyanBackground='\e[0;46m'
white='\e[0;37m'
whiteBold='\e[1;37m'
whiteBackground='\e[0;47m'
reset='\e[0m'

abort() {
    echo '
***************
*** ABORTED ***
***************
    ' >&2
    echo "An error occurred on line $1. Exiting..." >&2
    date -Iseconds >&2
    exit 1
}

trap 'abort $LINENO' ERR
set -e -o pipefail

quit() {
    trap : 0
    exit 0
}

# Asks if [Yn] if script shoud continue, otherwise exit 1
# $1: msg or nothing
# Example call 1: askContinueYn
# Example call 1: askContinueYn "Backup DB?"
askContinueYn() {
    if [[ $1 ]]; then
        msg="$1 "
    else
        msg=""
    fi

    # http://stackoverflow.com/questions/3231804/in-bash-how-to-add-are-you-sure-y-n-to-any-command-or-alias
    read -e -p "${msg}Continue? [Y/n] " response
    response=${response,,}    # tolower
    if [[ $response =~ ^(yes|y|)$ ]] ; then
        # echo ""
        # OK
        :
    else
        echo "Aborted"
        exit 1
    fi
}

# Reference: https://gist.github.com/steinwaywhw/a4cd19cda655b8249d908261a62687f8

echo "Checking Protoc version..."
VERSION=$(curl -sL https://github.com/protocolbuffers/protobuf/releases/latest | grep -E "<title>" | perl -pe's%.*Protocol Buffers v(\d+\.\d+(\.\d+)?).*%\1%')
BASEVERSION=4
echo

interactive=true
check_version=true

while test $# -gt 0; do
    case $1 in
        -h|--help)
            echo "Upgrade Protoc"
            echo
            echo "$0 [options]"
            echo
            echo "Options:"
            echo "-a                      Automatic mode"
            echo "-C                      Ignore version check"
            echo "-h, --help              Help"
            quit
            ;;
        -a)
            interactive=false
            shift
            ;;
        -C)
            check_version=false
            shift
            ;;
    esac
done

BIN="$HOME/bin"
DOWNLOADS="$HOME/downloads"

PIP="pip3.11"
PIPENV="python3.11 -m pipenv"

# Upgrade protoc

DEST="protoc"

OLDVERSION=$(cat $BIN/$DEST/.VERSION.txt || echo "")
echo -e "\nProtoc remote version $VERSION\n"
echo -e "Protoc local version: $OLDVERSION\n"

if [ "$OLDVERSION" != "$VERSION" ]; then
    echo "Upgrade protoc from $OLDVERSION to $VERSION"

    NAME="protoc-$VERSION"
    ARCHIVE="$NAME.zip"

    mkdir -p $DOWNLOADS
    # https://github.com/protocolbuffers/protobuf/releases/download/v21.6/protoc-21.6-linux-x86_64.zip
    cmd="wget --trust-server-names https://github.com/protocolbuffers/protobuf/releases/download/v$VERSION/protoc-$VERSION-linux-x86_64.zip -O $DOWNLOADS/$ARCHIVE"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="echo -e '\nSize [Byte]'; stat --printf='%s\n' $DOWNLOADS/$ARCHIVE; echo -e '\nMD5'; md5sum $DOWNLOADS/$ARCHIVE; echo -e '\nSHA256'; sha256sum $DOWNLOADS/$ARCHIVE;"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="mkdir -p $BIN/$NAME; unzip $DOWNLOADS/$ARCHIVE -d $BIN/$NAME"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="echo $VERSION > $BIN/$NAME/.VERSION.txt; echo $VERSION > $BIN/$NAME/.VERSION_$VERSION.txt"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="[ -d $BIN/$DEST.old ] && rm -rf $BIN/$DEST.old || echo 'No old dir to delete'"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="[ -d $BIN/$DEST ] && mv -iT $BIN/$DEST $BIN/$DEST.old || echo 'No previous dir to keep'"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="mv -iT $BIN/$NAME $BIN/$DEST"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="rm $DOWNLOADS/$ARCHIVE"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    cmd="$BIN/$DEST/bin/protoc --python_out=protobuf_generated_python google_auth.proto"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"

    # Update README.md

    cmd="perl -i -pe 's%proto(buf|c)([- ])(\d\.)?$OLDVERSION%proto\$1\$2\${3}$VERSION%g' README.md && perl -i -pe 's%(protobuf/releases/tag/v)$OLDVERSION%\${1}$VERSION%g' README.md"
    if $interactive ; then askContinueYn "$cmd"; fi
    eval "$cmd"
else
    echo -e "\nVersion has not changed. Quit"
fi


# Upgrade pip requirements

cmd="sudo pip install --upgrade pip"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

$PIP --version

cmd="$PIP install -U -r requirements.txt"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

cmd="$PIP install -U -r requirements-dev.txt"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

cmd="$PIP install -U pipenv"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

$PIPENV --version

cmd="$PIPENV update && $PIPENV --rm && $PIPENV install"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

$PIPENV run python --version

# Test

cmd="pytest"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

cmd="$PIPENV run pytest"
if $interactive ; then askContinueYn "$cmd"; fi
eval "$cmd"

quit

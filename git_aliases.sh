# Git Shell Aliases
# Add these to your .zshrc or .bashrc
alias gst='git status'
alias ga='git add'
alias gaa='git add --all'
alias gcm='git commit -m'
alias gca='git commit --amend'
alias gco='git checkout'
alias gcb='git checkout -b'
alias gp='git push'
alias gpf='git push --force-with-lease'
alias gpl='git pull'
alias glog="git log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"
alias gd='git diff'
alias gds='git diff --staged'
alias gst='git stash'
alias gsp='git stash pop'
alias gsl='git stash list'
alias grb='git rebase'
alias grba='git rebase --abort'
alias grbc='git rebase --continue'
alias gcp='git cherry-pick'

# Git Config Aliases
# Run these commands to set them in your .gitconfig
# git config --global alias.st status
# git config --global alias.co checkout
# git config --global alias.br branch
# git config --global alias.cm commit
# git config --global alias.unstage 'reset HEAD --'
# git config --global alias.last 'log -1 HEAD'

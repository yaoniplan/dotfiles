<!-- What the project does -->
<!-- Why the project is useful -->

## How users can get started with the project
- #### Manage dotfiles with Git
    - First use
      ```
      git init --bare $HOME/.dotfiles
      echo "alias dotfiles='/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'" >> $HOME/.bashrc
      dotfiles config --local status.showUntrackedFiles no
      dotfiles status
      dotfiles add .bashrc
      dotfiles commit -m "Add .bashrc"
      dotfiles branch -M main
      dotfiles remote add origin git@github.com:yaoniplan/dotfiles.git
      dotfiles push -u origin main
      ```
    - Second machine
      ```
      git clone --bare https://github.com/yaoniplan/dotfiles.git $HOME/.dotfiles
      alias dotfiles='/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'
      dotfiles checkout
      ```
- ***Notes***
    - Replace *.bashrc* with your dotfiles
    - Replace *yaoniplan* with your user name
- ***References***
    - https://fwuensche.medium.com/how-to-manage-your-dotfiles-with-git-f7aeed8adf8b
    - https://medium.com/@simontoth/best-way-to-manage-your-dotfiles-2c45bb280049

<!-- Where users can get help with your project -->
<!-- Who maintains and contributes to the project-->

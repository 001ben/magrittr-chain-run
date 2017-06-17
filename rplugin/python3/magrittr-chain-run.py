import neovim
import re

@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim

    def getLineEndMatch(self, line):
        # Return a match in group(2) if line followed by %>%, %T>%, or +
        return re.search('(.*?)((?:%T?>%|\+|,)\s*(#.*)?$|$)', line) 

    def isBlankLineOrComment(self, line):
        return (re.search('^\s*$', line) or re.search('^\s*#', line)) != None

    def removeAssignmentOperator(self, line):
        return re.search('(?:^.*<-|^)(.*?)(?:->.*$|$)', line).group(1)

    @neovim.function('RunFullMagrittrChain')
    def runFullMagrittrChain(self, args):
        self.runMagrittrChain('full')

    @neovim.function('RunMagrittrChain')
    def runMagrittrChain(self, args):
        # Get the current line and add to the chain_to_run buffer
        ln = self.vim.current.window.cursor[0]-1
        current_line=self.vim.current.buffer[ln]

        # Just return if the line being run is whitespace
        if self.isBlankLineOrComment(current_line):
            return

        # Get the current line without the pipe or plus symbol
        match=self.getLineEndMatch(current_line)
        chain_to_run=[match.group(1)]

        # Iterate upwards until reaching a line without pipe or plus
        ln -= 1
        found_start=False
        while(ln>=0 and not found_start):
            current_line = self.vim.current.buffer[ln]
            if self.isBlankLineOrComment(current_line):
                chain_to_run.append(current_line)
            else:
                match = self.getLineEndMatch(current_line)
                if(not match.group(2)):
                    found_start=True
                else:
                    chain_to_run.append(match.group(0))
            ln -= 1

        # Remove any assignment operator on the last line(->)
        if(args!='full'):
            chain_to_run[0] = self.removeAssignmentOperator(chain_to_run[0])

        # After dealing with last line, reverse the array because we've been appending lines as we move up
        chain_to_run.reverse()

        # Remove all preceding blank lines and comments
        while(self.isBlankLineOrComment(chain_to_run[0])):
            chain_to_run.pop(0)

        # Remove the assignment operator at the start (if exists) and clean up
        if(args!='full'):
            chain_to_run[0] = self.removeAssignmentOperator(chain_to_run[0])

        chain_to_run = map(lambda x: x.strip(), chain_to_run)
        command = '\n'.join(chain_to_run) \
            .replace("'", "''")

        self.vim.command("call g:SendCmdToR('%s')"%command)
        return

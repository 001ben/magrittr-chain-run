import neovim
import re
import rpy2
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr

def get_test():
    exec(open('./rplugin/python3/magrittr-chain-run.py').read())
    import neovim
    import os
    nvim = neovim.attach('socket', path=os.environ['NVIM_LISTEN_ADDRESS'])
    return Main(nvim)

def do_test_stuff():
    m = get_test()

@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim
        self.get_last_expression = robjects.r("""
        library(base)
        library(rlang)
        library(stringr)
        library(purrr)
        get_last_expression = function(xx, remove_assignment) {
          parse_success = TRUE
          e = tryCatch(rlang::parse_exprs(xx), error = function(e) {
            parse_success <<- FALSE
            list(0, FALSE, e, str_detect(e$message, 'unexpected'))
          })
          if(!parse_success) return(e)
          n_e = length(e)
          l_e = dplyr::last(e)
          if(remove_assignment && length(l_e) > 1 && as.character(l_e[[1]]) %in% c('=', '<-', '->')) {
            r_e = expr_text(l_e[[3]],width=500L)
          } else {
            r_e = expr_text(l_e, width=500L)
          }
          list(n_e, str_replace_all(str_replace_all(r_e, '\n', ''), '%>%', '%>%\n '), list(), FALSE) 
        }
        """)

    def getLineEndMatch(self, line):
        # Return a match in group(2) if line followed by %>%, %T>%, or +
        return re.search('(.*?)((?:%T?>%|\\+|&|\\||,|\\()\\s*(#.*)?$|$)', line) 

    def getPrevLineStartMatch(self, line):
        # Return a match in group(1) if line started by a continuation char
        return re.search('(^\\s*)(,|\\+|\\$|\\))', line) 

    def isBlankLineOrComment(self, line):
        return (re.search('^\\s*$', line) or re.search('^\\s*#', line)) != None

    def removeAssignmentOperator(self, line):
        return re.search('(?:^.*%?<-%?|^)(.*?)(?:%?->%?.*$|$)', line).group(1)

    @neovim.function('RunFullMagrittrChain')
    def runFullMagrittrChain(self, args):
        self.runMagrittrChain('full')

    def runExpressionChain(self, remove_assignment):
        # Get the current line and add to the chain_to_run buffer
        ln = self.vim.current.window.cursor[0]-1
        current_line=self.vim.current.buffer[ln]
        
        # Just return if the line being run is whitespace
        if self.isBlankLineOrComment(current_line):
            return
        
        # Get the current line without the pipe or plus symbol
        match=self.getLineEndMatch(current_line)
        chain_to_run=match.group(1)
        init = self.get_last_expression(chain_to_run, remove_assignment)
        if init[3][0]:
            done = True
            raise Exception('Cannot run line with open brackets')
            #  self.vim.command('echoerr "Cannot run line with open brackets"', async_=True)
            #  self.vim.call('echoerr', "Cannot run line with open brackets")
            #  self.vim.err_write('Cannot run line with open brackets', async_=True)
            return
            #  exp = chain_to_run
        else:
            done = False
        
        # Iterate upwards until there's more than one expression
        while(ln > 0 and not done):
            ln -= 1
            print('>>> line number %s' % (ln))
            next_item = self.vim.current.buffer[ln]
            chain_plus = next_item + '\n' + chain_to_run
            print('chain_plus:\n%s' % chain_plus)
            e = self.get_last_expression(chain_plus, remove_assignment)
            if e[3][0]:
                print('line unexpected end of input, returning chain_to_run')
                chain_plus
                exp = self.get_last_expression(chain_to_run, remove_assignment)[1][0]
                done=True
            elif e[0][0] > 1:
                print('more than 1 expression, returning it')
                exp = e[1][0]
                done=True
            else:
                print('continuing, making chain_to_run == chain_plus')
                chain_to_run = chain_plus
        
        if not done:
            try_exp = self.get_last_expression(chain_to_run, remove_assignment)[1][0]
            if not try_exp:
                exp = chain_to_run
            else:
                exp = try_exp
        
        command = exp.replace("'", "''")
        self.vim.command("call g:MySendCmdToR('%s')"%command)
        return

    @neovim.function('RunNewMagrittrChain')
    def runNewMagrittrChain(self, args):
        self.runExpressionChain(True)

    @neovim.function('RunFullNewMagrittrChain')
    def runFullNewMagrittrChain(self, args):
        self.runExpressionChain(False)

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
        prev_line=current_line
        found_start=False
        while(ln>=0 and not found_start):
            current_line = self.vim.current.buffer[ln]
            if self.isBlankLineOrComment(current_line):
                chain_to_run.append(current_line)
            else:
                match = self.getLineEndMatch(current_line)
                prev_match = self.getPrevLineStartMatch(prev_line)
                if(not match.group(2) and prev_match is None):
                    found_start=True
                else:
                    chain_to_run.append(match.group(0))
            prev_line = current_line
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
        
        self.vim.command("call g:MySendCmdToR('%s')"%command)
        return

import { Tab } from '@headlessui/react'
import clsx from 'clsx'
import CopyButton from 'components/common/CopyButton'
import { Fragment } from 'react'

export const CliInstallCommands = () => {
  const fromSource =
    'git clone https://github.com/Dos2Locos/libreseal-cli.git && cd libreseal-cli && ./scripts/install-from-source.sh'
  const platformScripts = [
    {
      name: 'From source (Linux / macOS)',
      rawScript: fromSource,
      styledScript: (
        <div className="space-y-1">
          <pre>
            <span className="text-emerald-800 dark:text-emerald-300">git</span> clone
            https://github.com/Dos2Locos/libreseal-cli.git
          </pre>
          <pre>
            <span className="text-emerald-800 dark:text-emerald-300">cd</span> libreseal-cli &&
            ./scripts/install-from-source.sh
          </pre>
        </div>
      ),
    },
    {
      name: 'Go toolchain',
      rawScript:
        'git clone https://github.com/Dos2Locos/libreseal-cli.git && cd libreseal-cli/src && go build -o libreseal . && sudo install libreseal /usr/local/bin/',
      styledScript: (
        <div className="space-y-1">
          <pre>
            <span className="text-emerald-800 dark:text-emerald-300">cd</span> libreseal-cli/src
            && <span className="text-emerald-800 dark:text-emerald-300">go</span> build -o
            libreseal .
          </pre>
          <pre>
            <span className="text-emerald-800 dark:text-emerald-300">sudo</span> install libreseal
            /usr/local/bin/
          </pre>
        </div>
      ),
    },
  ]
  return (
    <Tab.Group>
      <Tab.List className="flex gap-1 overflow-x-auto rounded-t-lg border border-neutral-500/40 bg-zinc-800 text-2xs font-medium md:gap-2 md:px-4">
        {platformScripts.map((platform) => (
          <Tab as={Fragment} key={platform.name}>
            {({ selected }) => (
              <button
                className={clsx(
                  'ease shrink-0 border-b p-2 outline-none transition focus:outline-none',
                  selected
                    ? 'border-emerald-500 text-emerald-500'
                    : 'border-transparent text-neutral-400 hover:text-neutral-200'
                )}
              >
                {platform.name}
              </button>
            )}
          </Tab>
        ))}
      </Tab.List>
      <Tab.Panels>
        {platformScripts.map((platform) => (
          <Tab.Panel as={Fragment} key={platform.name}>
            <div className="group relative overflow-x-auto rounded-b-lg border-x border-b border-neutral-500/40 bg-zinc-300/50 dark:bg-zinc-800/50 p-3 text-left text-xs text-zinc-900 dark:text-zinc-100">
              <code>{platform.styledScript}</code>
              <div className="absolute right-4 top-3.5 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                <CopyButton value={platform.rawScript} />
              </div>
            </div>
          </Tab.Panel>
        ))}
      </Tab.Panels>
    </Tab.Group>
  )
}

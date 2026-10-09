# OpenWin

**What if Windows were open source?** OpenWin installs Windows 11 the way an
open-source operating system would ship: open-source apps out of the box,
without Edge and most of the preinstalled apps, and with a local account instead
of a Microsoft account.

It's an answer file for Windows Setup (`autounattend.xml`) plus an `$OEM$`
folder with everything it installs. You add them to the official Windows 11
installer from Microsoft, either on a USB drive or in a virtual machine.

## Downloads

| File | Use it for |
| --- | --- |
| [**OpenWin.zip**](https://github.com/cris2k47/OpenWin/releases/latest/download/OpenWin.zip) | A USB drive made with the Media Creation Tool |
| [**autounattend.iso**](https://github.com/cris2k47/OpenWin/releases/latest/download/autounattend.iso) | A virtual machine |

Both contain the same two things, `autounattend.xml` and the `$OEM$` folder,
and always ship the latest Brave and 7-Zip (see [Always up to date](#always-up-to-date)).

## What you get

**Open-source apps by default**
- **Brave** is the default browser and PDF viewer, pinned to the taskbar, and
  follows the Windows display language. Each user starts with these settings,
  which they can change later in Brave's settings:
  - No Brave VPN, Leo AI, Wallet or Rewards buttons, and no Leo AI, Brave Talk
    or Wallet in the sidebar.
  - No Leo suggestions in the address bar or Leo items in the right-click menu,
    and no Brave Commands suggestions.
  - A New Tab page with a clock, without sponsored images, Brave News or the
    Rewards, Talk and VPN widgets.
  - Downloads go straight to the Downloads folder without asking where.
  - No welcome page the first time Brave opens, and Brave's anonymous usage
    statistics (P3A) are off.
  - Widevine is on, so streaming services that need DRM, such as Netflix and
    Spotify, play without asking first. Brave downloads it about a minute after
    it first opens; if a site says protected content isn't enabled before then,
    reload the page.
- **7-Zip** opens archives and disk images: zip, 7z, rar, tar, gz, xz, zst,
  iso, cab, wim, vhd(x), dmg and more.

**No bloat**
- Microsoft Edge is uninstalled.
- These preinstalled apps are removed: Clipchamp, Clock, Camera, Copilot,
  Dev Home, Family, Feedback Hub, Get Help, News, Outlook (new), Phone Link,
  Power Automate, Quick Assist, Solitaire Collection, Sound Recorder, Sticky
  Notes, Teams, Terminal, To Do, Weather, Widgets and Xbox.
- OneDrive isn't set up for new users.
- The Start menu only has Brave, Microsoft Store, Settings, Photos, Paint,
  Calculator, Notepad, Snipping Tool and File Explorer. The taskbar has File
  Explorer and Brave.
- No web suggestions in Search.

**Sensible defaults**
- Dark theme and the classic right-click menu.
- File Explorer opens to This PC and shows file extensions and hidden files.
- Mouse acceleration is off.
- Windows Update doesn't replace your drivers.

**Easier setup**
- Works on PCs without TPM 2.0, Secure Boot or 4 GB of RAM.
- Uses a local account: no Microsoft account and no internet connection needed.
- Skips the privacy settings screen, leaving its optional settings off.

## Install from a USB drive

1. Make a Windows 11 USB drive with the [Media Creation Tool](https://www.microsoft.com/software-download/windows11).
2. Download [OpenWin.zip](https://github.com/cris2k47/OpenWin/releases/latest/download/OpenWin.zip) and extract it.
3. Copy `autounattend.xml` and the `$OEM$` folder to the root of the USB drive,
   next to `setup.exe`.
4. Boot the PC from the USB drive.

## Install in a virtual machine

1. Download the Windows 11 ISO from [Microsoft](https://www.microsoft.com/software-download/windows11)
   and [autounattend.iso](https://github.com/cris2k47/OpenWin/releases/latest/download/autounattend.iso).
2. Create the virtual machine with at least 2 CPUs and the Windows 11 ISO as its
   boot CD/DVD drive. Windows 11 Setup refuses machines with a single CPU.
3. Add a second CD/DVD drive with `autounattend.iso`.
4. Start the virtual machine and press a key when it says *Press any key to boot
   from CD or DVD*. Windows Setup finds `autounattend.xml` on the second drive
   by itself.

Tips for some hypervisors:
- **VirtualBox**: turn off VirtualBox's own unattended installation when you
  create the machine: untick *Proceed with Unattended Installation* (VirtualBox
  7.2 and later) or tick *Skip Unattended Installation* (7.0 and 7.1).
  Otherwise VirtualBox installs Windows with its own answer file and OpenWin is
  ignored. Then add the second drive in *Settings → Storage*.
- **VMware Workstation**: choose *I will install the operating system later*
  to avoid Easy Install, then add the second CD/DVD drive.
- **Hyper-V**: use a Generation 2 machine. The wizard gives it 1 virtual
  processor, so set *Settings → Processor* to 2 or more, and add the second DVD
  drive to its SCSI controller.
- **virt-manager / QEMU**: add a second CDROM device.

## What Setup still asks you

- Your language, time format and keyboard.
- Where to install Windows. **Setup can erase the drive you pick, so back up first.**
- Your region and keyboard layout.
- On a PC without a wired connection, a Wi-Fi network. Choose *I don't have
  internet* to stay offline.
- A name and password for your account, plus three security questions if you
  set a password.

## Activation

OpenWin installs Windows 11 Pro with Microsoft's generic installation key,
which doesn't activate Windows. A PC with a Windows 10 or 11 Pro digital license
activates on its own once it's online. Otherwise, enter your own Pro key in
*Settings → System → Activation*.

## Always up to date

Every 5 minutes, a [GitHub Actions workflow](.github/workflows/update-installers.yml)
checks for new releases of Brave and 7-Zip. When one is out, it verifies the
official installer against the checksums the publisher provides (signed by
Brave, for Brave), commits the update to this repository and publishes a new
release with the downloads above.

Brave's offline installer is larger than GitHub's 100 MB file limit, so this
repository keeps only its version and checksum, in `Brave.json`. The downloads
above include the installer itself.

## Repository layout

```
autounattend.xml          Answer file for Windows Setup
$OEM$/$$/                 Copied to C:\Windows
  Setup/Scripts/          Scripts that run during setup
  Setup/Files/            7-Zip installer, Brave.json and registry tweaks
  System32/               Default apps
$OEM$/$1/                 Copied to C:\ (Brave settings, Start menu and taskbar layout)
.github/                  The workflow that keeps everything up to date
```

## Credits

- [Brave](https://brave.com/) by Brave Software, under the Mozilla Public License 2.0.
- [7-Zip](https://www.7-zip.org/) by Igor Pavlov, under the GNU LGPL with the unRAR restriction.

Windows is a trademark of Microsoft. OpenWin isn't affiliated with Microsoft,
Brave Software or 7-Zip.

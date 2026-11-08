---
title: TwoMillion HTB
slug: htb-twomillion-htb
date: 2026-11-08
platform: hack-the-box
category: Hack The Box
language: en
tags:
- linux
- web
- os_command_injection
- broken_access_control
difficulty: Easy
status: Partial
summary: "TwoMillion HTB walkthrough: breaking the invite flow, abusing broken access control, and turning it into OS command injection for a reverse shell."
---
![Nmap scan of the TwoMillion target](assets/2mil/nmap2mil.png)

## Scope

- Target / lab: Box

## Recon

First, I used Nmap with a SYN scan (`-sS`) and version detection (`-sV`) to find open ports and identify the services running on the target. I also used the aggressive timing template (`-T4`) to make the scan faster.

![Nmap scan results](assets/2mil/recon.png)

Port 80 (HTTP) was open, so I started by visiting the website in my browser.

![HTB landing page](assets/2mil/htblanding.png)

  This was the HTB landing page. There was not much to explore here, so I decided to log in and continue enumerating the website.

![Homepage after login attempt](assets/2mil/htbpage.png)

![Invite code required to sign up](assets/2mil/invite.png)

  An invite code was required to sign up. Without it, I could not continue. I intercepted the request to see how the invite-code process worked. I also tried a random invite code, but it was rejected.

![Random invite code rejected](assets/2mil/randominvite.png)

![Login failure after invalid invite code](assets/2mil/cantlogin.png)

  ![Page source showing the obfuscated invite JavaScript](assets/2mil/invitesource.png)

After a quick review of the page source, I noticed an interesting file: `/js/inviteapi.min.js`.

The invite-related JavaScript code was obfuscated, so it was difficult to read. I used a JavaScript deobfuscation tool such as [de4js](https://thanhle.io.vn/de4js/) to make the code easier to understand.

![Packed JavaScript before deobfuscation](assets/2mil/packed.png)

  To make the code clearer, I also used the unpacking feature built into [de4js](https://thanhle.io.vn/de4js/).

![Deobfuscated JavaScript in de4js](assets/2mil/de4js.png)

  The code was now easier to read. The `verifyInviteCode` function was used to send the invite code that I entered. Another function showed me the API endpoint for generating an invite code.

I used the `POST` method with `/api/v1/invite/how/to/generate` to get information about the invite-code generation process. The response also gave me a hint about the encoding method: ROT13 (a Caesar cipher).

![Invite generation endpoint returning a ROT13 hint](assets/2mil/genrot13.png)

![ROT13 decoding of the API response](assets/2mil/rot13.png)

[CyberChef](https://toolbox.itsec.tamu.edu/) is a useful tool for this kind of task. After decoding the response, I found the actual API endpoint.

I then used the `POST` method with `/api/v1/invite/generate`. This request should generate a valid invite code.

![Invite generation response in Base64](assets/2mil/genbase64.png)

The generated code was still encoded in Base64. I used a pipe (`|`) with `base64 -d` to decode it into plaintext.

![Decoded invite code from Base64](assets/2mil/base64-d.png)

Now I could use the invite code to sign up. The other pages did not seem to have much functionality. The `/acess` page was the only page I could interact with.

![Logged-in website interface](assets/2mil/htb-loged.png)

![VPN access page](assets/2mil/access.png)

This page allowed me to generate a VPN configuration file. After I clicked the `Regenerate` button, I received a VPN configuration file with my username in its filename. This made me wonder how the application handled the username on the server side and whether the input was properly checked.

![Generated VPN configuration file](assets/2mil/asd.ovpn.png)

I continued enumerating the website for other possible attack vectors. I fuzzed for hidden directories that could be accessed and filtered out the false-positive results.

![Directory fuzzing results](assets/2mil/fuzz.png)

![API directory listing response](assets/2mil/apidir.png)

Even though the response was `401 Unauthorized`, I decided to investigate the endpoint further.

When I visited `http://2million.htb/api`, I found the following response:

![API v1 response with available endpoints](assets/2mil/apiv1.png)

A large number of API endpoints were exposed. This revealed more information about the application's functionality (Information Disclosure).

![Full API endpoint listing](assets/2mil/fullapi.png)

## Exploit

At this point, I focused on getting an admin role so I could access and test more functionality.

![Admin authorization check](assets/2mil/adminauthf.png)

![Current user authorization response](assets/2mil/userauth.png)

I had tested almost every API endpoint, except for the endpoints used to generate a VPN configuration for a specific user and to update settings.

The VPN configuration feature caught my attention because the application used my username in the filename. I also wanted to investigate the `PUT` method, which is commonly used to update or replace data.

I sent a request to `PUT /api/v1/admin/settingws/update` to see how the endpoint responded. ![API request requiring JSON details](assets/2mil/needjson.png)
 The server indicated that the request body should be in JSON format, so I changed the `Content-Type` header to match.

![Settings update requiring an email parameter](assets/2mil/needemail.png)

![Settings update requiring the is_admin parameter](assets/2mil/needis_admin.png)

  The request still needed some parameters. I added the required parameters based on the server's responses.

![Updated settings request](assets/2mil/brokenacc.png)

If you remember the response from `GET /api/v1/user/auth`, the `is_admin` value was `0`. This meant that my account did not have an admin role.

After sending the API request, I gained the admin role, which should not be possible for a normal user (Broken Access Control). I checked the result again with `GET /api/v1/admin/auth`.

![Admin VPN generation page](assets/2mil/adminvpngen.png)

![Admin VPN configuration result](assets/2mil/adminvpnn.png)

Next, I wanted to confirm the suspected command injection vulnerability. I needed to check whether my input was executed together with the original command.

![Command injection timing test with sleep 4](assets/2mil/sleep4.png)

  A simple way to test command injection is to use a semicolon (`;`) to separate the original command from an additional command. For example: `command1; command2;`.

  Sometimes, an application may use filters, and different situations may require different ways to bypass them. For this test, I added the `sleep 4` command. If the command was executed successfully, the response should be delayed by about four seconds.

The test caused a delay of about four seconds, as I expected. However, confirmed that the command was executed by the operating system.

After that, I changed the command to `id` to check whether I could execute a command on the server and confirm Remote Code Execution (RCE).

![Command injection result showing id output](assets/2mil/id.png)

## FootHold

Next, I prepared to send a reverse shell. First, I checked my IP address to find the address that the target should connect back to.

![Local IP address from tun0](assets/2mil/ipatun0.png)

I used a [reverse shell generator](https://www.revshells.com/) to create a simple Bash payload. I encoded it with Base64 so that special characters would be easier to handle when sending it. After it reached the target, I decoded it and used Bash to execute the payload.

I started my listener and then sent the payload.

![Remote shell callback](assets/2mil/rce.png)

The shell was unstable, so I upgraded it first.

![Shell upgrade attempt](assets/2mil/shellupgrage.png)

![Unable to read the flag file](assets/2mil/cannotcat.png)

I found the location of the user flag, but I did not have permission to read it.

![Sensitive files discovered in the web root](assets/2mil/superdump.png)

While enumerating the web root further, I found some sensitive files. One of them was `.env`. This gave me more possible attack paths because the file could contain database credentials or other information that might also be useful for SSH access.

I used the discovered credentials to connect to the `admin` account over SSH and retrieve the flag.

![Flag retrieved over SSH](assets/2mil/catflag.png)

## Post Exploit Enumeration

To better understand how the OS command injection happened, I wanted to find the function that handled the VPN configuration file. I started by looking at the controller to understand how the backend processed the request.

![VPN controller code](assets/2mil/VPNconroller.png)

![Reviewing the VPN controller implementation](assets/2mil/conrollerreview.png)

This line is the main reason why the command injection vulnerability happens.

```
$output = shell_exec("/usr/bin/cat /var/www/html/VPN/user/$username.ovpn");
```

The application uses `shell_exec()` to run a system command and read the VPN configuration file. However, the `$username` variable comes from user input and is directly added to the command without proper validation.

Because `shell_exec()` runs the command through the system shell, an attacker can modify the username input to add extra commands. This can lead to arbitrary command execution on the server with the same permissions as the web server.

I want to get more experience with privilege escalation first. I will come back to this part when I am more familiar with the topic.

## What I have learned

I struggled with JavaScript deobfuscation because I do not have much experience with JavaScript yet. I was not sure how to start reading the obfuscated code.

- One thing I learned is that a payload does not always need to be complex. It is better to look at the bigger picture first. Once I understand how the application works, the next steps become easier to follow.

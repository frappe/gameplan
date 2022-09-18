<p align="center">
  <img src="https://user-images.githubusercontent.com/9355208/190904451-ac6f171b-26c6-4432-a04f-044974516da6.png" alt="Gameplan logo" height="50" />
  <p align="center">Delightful work communication tool that you'll actually enjoy using</p>
</p>

Gameplan is a work communication tool for teams who mostly work remote and prefer having meaningful discussions in an async format. We built it for ourselves because we were finding it difficult to keep track of so many conversations in our chat tool. Chat forces you to be online all the time and doesn't really have any concept of threaded discussions. Gameplan allows you to categorize your discussions around projects and teams. It also doubles up as your team's knowledge archive. You can surface important information and conclusions from your discussions into the readme's of your projects and teams.

## Features
- Organize discussions into projects which in turn are part of a team 🗄
- Surface important information for your project and team in the Readme 📝
- Simple layout that optimizes readability of discussions 🤓
- Customize your Team and Project with emojis 💅🏻
- People directory with each person's profile page 👨‍👩‍👧‍👦
- Set cover image, profile photo, short bio and a "About me" section 🦹🏼‍♀️
- Powerful search capabilities to find older discussions 🔍
- A common discussions feed that shows discussions from across projects and teams 📚
- Delightful user-experience in overall usage ✨

## Tech Stack

### Backend
Gameplan is built on [Frappe Framework](https://frappeframework.com) which is a batteries-included python web-framework.
These are some of the tools it's built on:
- [Python](https://www.python.org)
- [Redis](https://redis.io/)
- [MariaDB](https://mariadb.org/)
- [Socket.io](https://socket.io/)

### Frontend
The frontend of Gameplan is a VueJS SPA which uses a component library called [Frappe UI](https://github.com/frappe/frappe-ui).
These are some of the tools used on frontend:
- [VueJS](https://vuejs.org)
- [Frappe UI](https://github.com/frappe/frappe-ui)
- [TailwindCSS](https://tailwindcss.com)
- [HeadlessUI](https://headlessui.com)

## Deployment
Gameplan is an app built on top of Frappe Framework. So, you can follow any deployment guide for hosting a Frappe Framework based site.

### Managed Hosting
Gameplan can be deployed in a few clicks on [Frappe Cloud](https://frappecloud.com).

### Self hosting
If you want to self-host, you can follow official [Frappe Bench Installation](https://github.com/frappe/bench#installation) instructions.

## Discussions
If you have an idea that you think Gameplan should implement or you just want to hangout with other Gameplan users, you can join [Discussions](https://github.com/frappe/gameplan/discussions).

## Reporting Bugs
If you find any bugs, feel free to report them here on [GitHub Issues](https://github.com/frappe/gameplan/issues). Make sure you share enough information (app screenshots, browser console screenshots, stack traces, etc) for project maintainers to replicate your bug.

## License

AGPLv3

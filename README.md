let me start with i have no idea of what i'm doing

in my extensive 5 minute web search i didn't find any tool that did this without overly complicated settings and free.
So i told gemini to do it.

Surprisingly it works, so i'm uploading the whole thing to not lose it and if somebody ever stumbles upon this please enjoy and let me know how much stupid code gemini has put in it.

As for the important part: just install python, ollama and qwen 3.5 0.8b (i believe i used the standard ollama q4); then press Avvia_Renamer.command and it will open a localhost page on the browser just to have a little user interface.

that's it, choose a folder and start it; it uses basically no resources and it cleans the cache every n number of photos; so you can run it in the background and keep doing whatever.

my test case has been on an M1 Macbook Air, the cheap cheap one, with 8Gb of RAM and not even all the cores; it worked on around 64000 photos on an hdd, sometimes it forgets a file or ignore the instructions and rename the photo with 15 different words, so maybe smaller folders then my case are better suited or just break it down in batches.

other useful info:

• kv cache is q8, it grows awfully large even if the thing reduces the pictures to 500 and something pixels; i'm not sure what is happenining but it works.

• while i'm not sure i believe it's just for macos.

• fuck llama.cpp and mmproj (i can't use it i'm just ignorant).

• somewhere in the code are the options for the model and they are slightly modified but i don't remember them, basically really low temperature so it doesn't think it just acts. 

Last but not least i tried convincing the model to answer in other languages but it refuse to do so; so please help me there.

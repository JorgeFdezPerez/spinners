/*
 * Console app to test sockets of python apps
 * 
*/

using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using System.Text;
using System.Collections.Generic;
using System.Text.Json.Serialization;

class Program
{
    static async Task sendLoop(Socket client)
    {
        string[,] messagesToSend = {
            {"hmiEvent","resetPlant"},
            {"hmiEvent","manualSelected"},
            {"hmiEvent","recipeSelected"}
        };

        for (int i = 0; i<messagesToSend.GetLength(0); i++)
        {
            Dictionary<string, string> message = new();
            message.Add(messagesToSend[i,0], messagesToSend[i,1]);
            var bytesToSend = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(message) + "\r\n");
            await client.SendAsync(bytesToSend);
        }
    }
    static async Task receiveLoop(Socket client)
    {
        bool connected = true;
        string receiveBuffer = new string("");
        while (connected)
        {
            //Recieve messages
            byte[] buffer = new byte[1_024];
            while (connected && !receiveBuffer.Contains("\r\n"))
            {
                //Note: if received == 0, connection is ended
                var received = await client.ReceiveAsync(buffer, SocketFlags.None);
                if (received == 0)
                {
                    connected = false;
                    Console.Write("Socket disconnected\r\n");
                }
                else
                    receiveBuffer += Encoding.UTF8.GetString(buffer);
            }
            if (connected)
            {
                var splitMessage = receiveBuffer.Split("\r\n", 2); //Split buffer at the first instance on the EOM
                receiveBuffer = splitMessage[1];
                Console.Write("Received: ");
                Console.Write(splitMessage[0]);
                Console.Write("\r\n");
                var messageReceived = JsonSerializer.Deserialize<Dictionary<string, string>>(splitMessage[0]);
            }
        }
    }
    static async Task Main(string[] args)
    {
        const int PORT = 10000;

        //Get IP of the python devcontainer
        IPHostEntry serverHostInfo = Dns.GetHostEntry("spinners-dev-python");
        IPAddress serverIPAddress = serverHostInfo.AddressList[0];
        IPEndPoint serverIPEndpoint = new(serverIPAddress, PORT);

        using Socket client = new(
            serverIPEndpoint.AddressFamily,
            SocketType.Stream,
            ProtocolType.Tcp
        );

        // Should try-catch for exceptions if server is not active
        client.Connect(serverIPEndpoint);

        Task sendTask = sendLoop(client);
        Task receiveTask = receiveLoop(client);

        /*
        Dictionary<string, string> message = new();
        message.Add("Event", "Start");
        var bytesToSend = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(message) + "\r\n");
        await client.SendAsync(bytesToSend);

        Console.Write("SENT\r\n");
        
        bool connected = true;
        string receiveBuffer = new string("");
        while (connected)
        {
            //Recieve messages
            byte[] buffer = new byte[1_024];
            while (connected && !receiveBuffer.Contains("\r\n"))
            {
                //Note: if received == 0, connection is ended
                var received = await client.ReceiveAsync(buffer, SocketFlags.None);
                if (received == 0)
                {
                    connected = false;
                    Console.Write("Socket disconnected\r\n");
                }
                else
                    receiveBuffer += Encoding.UTF8.GetString(buffer);
            }
            if (connected)
            {
                var splitMessage = receiveBuffer.Split("\r\n", 2); //Split buffer at the first instance on the EOM
                receiveBuffer = splitMessage[1];
                Console.Write(splitMessage[0]);
                Console.Write("\r\n");
                Console.Write(splitMessage[1]);
                Console.Write("\r\n");
                var messageReceived = JsonSerializer.Deserialize<Dictionary<string, string>>(splitMessage[0]);
                Console.Write(messageReceived);
                Console.Write("\r\n");
            }
        }*/
    }
}

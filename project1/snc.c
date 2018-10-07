#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h> 

// helpers for error messages
void inputerr() {
    fprintf(stderr, "invalid or missing options\nusage: ./snc [-l] [-u] [hostname] portno\n");
    exit(1);
}

void othererr() {
    // perror("err"); // debug
    fprintf(stderr, "internal error\n");
    exit(1);
}

// server
void server_func(struct hostent *client, int portno, int dgramflag) {
    int sockfd, newsockfd, clilen, n;
    char buffer[256];
    struct sockaddr_in serv_addr, cli_addr;

    // if -u is on, use UDP
    if (dgramflag)
        sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    else
        sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) othererr();

    bzero((char *) &serv_addr, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    // if no client specified, use INADDR_ANY
    if (client == NULL)
        serv_addr.sin_addr.s_addr = INADDR_ANY;
    else
        bcopy((char *)client->h_addr, 
            (char *)&serv_addr.sin_addr.s_addr,
            client->h_length);
    serv_addr.sin_port = htons(portno);

    if (bind(sockfd, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0)
        othererr();

    listen(sockfd, 5);
    clilen = sizeof(cli_addr);
    newsockfd = accept(sockfd, (struct sockaddr *) &cli_addr, &clilen);
    if (newsockfd < 0) othererr();

    bzero(buffer, 256);
    // infite loop until cancelled with ctrl+D or if client exits
    while (1) {
        // recv msg from client
        n = read(newsockfd, buffer, 255);
        if (n < 0) othererr();
        if (n == 0) break; // client exits
        printf("%s", buffer);

        bzero(buffer, 256); // clean buffer
    }

    if (close(sockfd) < 0) othererr();
    return;
}

// client
void client_func(struct hostent *server, int portno, int dgramflag) {
    int sockfd, n;
    char buffer[256];
    struct sockaddr_in serv_addr;

    if (dgramflag)
        sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    else
        sockfd = socket(AF_INET, SOCK_STREAM, 0);

    bzero((char *) &serv_addr, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    // connect to a specific server
    bcopy((char *) server->h_addr, 
        (char *) &serv_addr.sin_addr.s_addr,
        server->h_length);
    serv_addr.sin_port = htons(portno);

    if (connect(sockfd, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0)
        othererr();

    // infinite loop while input, unless cancelled or server exits
    bzero(buffer, 256);
    while (1) {
        fgets(buffer, 255, stdin);
        // send msg to server
        n = write(sockfd, buffer, strlen(buffer));
        if (n < 0) othererr();
        if (n == 0) break;

        bzero(buffer, 256);
    }

    if (close(sockfd) < 0) othererr();
    return;
}

int main(int argc, char **argv) {
    int serverflag = 0, dgramflag = 0;
    int sockfd, portno;
    char *hostname;
    struct hostent *conn = NULL;

    // client: ./snc localhost 9999
    // server: ./snc -l 9999 or ./snc -l localhost 9999
    if (argc < 3) inputerr();
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-l"))
            serverflag = 1;
        else if (!strcmp(argv[i], "-u"))
            dgramflag = 1;
    }
    hostname = argv[argc-2];
    portno = atoi(argv[argc-1]);
    if (serverflag && (!strcmp(hostname, "-u") || !strcmp(hostname, "-l")))
        hostname = NULL;
    if (portno < 1024) inputerr();
    if (!serverflag && hostname == NULL) inputerr();

    // specific server to connect to / specific client to listen to
    if (hostname != NULL) {
        conn = gethostbyname(hostname);
        if (conn == NULL) othererr();
    }
    
    if (serverflag)
        server_func(conn, portno, dgramflag);
    else
        client_func(conn, portno, dgramflag);
}